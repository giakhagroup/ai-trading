import TradingView from '@mathieuc/tradingview';
import pino from 'pino';
import { MarketDataProvider, ProviderCapabilities, CanonicalCandle } from '../core/interfaces';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

interface SubscriptionConfig {
    symbol: string;
    timeframe: string;
    onUpdate: (candle: CanonicalCandle) => void;
    indicatorsToAttach: string[];
}

export class TradingViewProvider implements MarketDataProvider {
    public name = 'TradingView';
    public capabilities: ProviderCapabilities = {
        realtime: true,
        historical: true,
        quotes: true,
        ohlcv: true,
        multiSymbol: true,
        multiTimeframe: true,
        builtInIndicators: true,
        pineIndicators: false,
        replay: false,
        screener: false
    };

    private client: any;
    private isConnected: boolean = false;
    private isConnecting: boolean = false;
    private activeSessions: Map<string, any> = new Map();
    
    // QUANT REQUIREMENT: Store entire state of the current forming candle
    private activeCandles: Map<string, CanonicalCandle> = new Map();
    
    // SECURITY REQUIREMENT: Keep track of subscriptions to restore on reconnect
    private subscriptionConfigs: Map<string, SubscriptionConfig> = new Map();

    public async connect(): Promise<void> {
        if (this.isConnected || this.isConnecting) return;
        this.isConnecting = true;
        
        return new Promise((resolve, reject) => {
            try {
                this.client = new TradingView.Client();
                
                this.client.onError((err: any) => {
                    logger.error({ err }, 'TradingView Client Error');
                });
                
                this.client.onDisconnected(() => {
                    logger.warn('TradingView Socket Disconnected. Reconnecting...');
                    this.isConnected = false;
                    this.isConnecting = false;
                    this.handleReconnect();
                });
                
                this.isConnected = true;
                this.isConnecting = false;
                logger.info('TradingView Provider connected.');
                resolve();
            } catch (err) {
                this.isConnecting = false;
                logger.error({ err }, 'Failed to connect to TradingView');
                reject(err);
            }
        });
    }
    
    private async handleReconnect() {
        // Simple Exponential Backoff logic can be implemented here. For now, reconnect after 5 seconds.
        setTimeout(async () => {
            try {
                await this.connect();
                // Restore all subscriptions
                const configs = Array.from(this.subscriptionConfigs.values());
                this.activeSessions.clear(); // Clear old sessions before recreating
                for (const config of configs) {
                    await this.subscribe(config.symbol, config.timeframe, config.onUpdate, config.indicatorsToAttach, true);
                    // Slight delay to avoid burst on reconnect
                    await new Promise(res => setTimeout(res, 500));
                }
            } catch (e) {
                logger.error('Failed to reconnect, retrying later...');
                this.handleReconnect();
            }
        }, 5000);
    }

    public async disconnect(): Promise<void> {
        if (!this.isConnected || !this.client) return;
        this.client.end();
        this.isConnected = false;
        this.activeSessions.clear();
        this.activeCandles.clear();
        this.subscriptionConfigs.clear();
        logger.info('TradingView Provider disconnected.');
    }

    public async subscribe(
        symbol: string,
        timeframe: string,
        onUpdate: (candle: CanonicalCandle) => void,
        indicatorsToAttach: string[] = ['STD;Relative_Strength_Index'],
        isReconnect: boolean = false
    ): Promise<void> {
        if (!this.isConnected) {
            throw new Error('Provider is not connected');
        }

        const sessionKey = `${symbol}_${timeframe}`;
        
        // Save config for reconnect purposes
        if (!isReconnect) {
            this.subscriptionConfigs.set(sessionKey, { symbol, timeframe, onUpdate, indicatorsToAttach });
        }

        if (!this.activeSessions.has(sessionKey)) {
            const chart = new this.client.Session.Chart();
            chart.setMarket(symbol, { timeframe });
            
            chart.onError((...err: any[]) => {
                logger.error({ err }, `Chart Error for ${symbol}`);
            });

            const studies: any[] = [];
            const indicatorValues: Record<string, number> = {};

            for (const indicatorName of indicatorsToAttach) {
                try {
                    let indicator;
                    if (indicatorName.startsWith('STD;') || indicatorName.includes('@')) {
                        indicator = new TradingView.BuiltInIndicator(indicatorName);
                    } else {
                        indicator = await TradingView.getIndicator(indicatorName);
                    }
                    const study = new chart.Study(indicator);
                    study.onUpdate(() => {
                        if (study.periods && study.periods[0]) {
                            const val = study.periods[0].Plot ?? study.periods[0].RSI ?? study.periods[0].val ?? study.periods[0].Volume;
                            indicatorValues['RSI'] = typeof val === 'number' ? val : 30.0;
                        }
                    });
                    studies.push(study);
                    logger.info(`Attached indicator study ${indicatorName} to ${symbol}`);
                } catch (e: any) {
                    logger.warn(`Could not attach indicator ${indicatorName}: ${e.message}`);
                }
            }

            chart.onUpdate(() => {
                if (!chart.periods[0]) return;
                const tvCandle = chart.periods[0];
                const tickTime = tvCandle.time * 1000;
                
                const activeState = this.activeCandles.get(sessionKey);
                
                // QUANT ROLLOVER & DISCARD LOGIC
                if (activeState) {
                    if (tickTime < activeState.source_timestamp) {
                        // DISCARD out-of-order/stale data
                        return;
                    }
                    
                    if (tickTime > activeState.source_timestamp) {
                        // ROLLOVER: Emit previous candle as closed
                        const closedCandle = { ...activeState, is_closed: true };
                        onUpdate(closedCandle);
                        
                        // Proceed to create new state below
                    } else {
                        // UPDATE: Same timestamp, just update state and emit as forming
                        const updatedState: CanonicalCandle = {
                            ...activeState,
                            open: tvCandle.open,
                            high: tvCandle.high,
                            low: tvCandle.low,
                            close: tvCandle.close,
                            volume: tvCandle.volume,
                            indicators: { ...indicatorValues }
                        };
                        this.activeCandles.set(sessionKey, updatedState);
                        onUpdate(updatedState);
                        return;
                    }
                }
                
                // Create new forming candle state
                const newState: CanonicalCandle = {
                    event_id: `${symbol}-${tvCandle.time}`,
                    provider: this.name,
                    provider_symbol: symbol,
                    internal_symbol: symbol,
                    exchange: symbol.split(':')[0] || 'UNKNOWN',
                    asset_class: 'STOCK',
                    currency: 'VND',
                    timezone: 'Asia/Ho_Chi_Minh',
                    timeframe: timeframe,
                    
                    source_timestamp: tickTime,
                    event_timestamp: Date.now(),
                    received_at: Date.now(),
                    processed_at: Date.now(),
                    
                    open: tvCandle.open,
                    high: tvCandle.high,
                    low: tvCandle.low,
                    close: tvCandle.close,
                    volume: tvCandle.volume,
                    
                    is_closed: false,
                    sequence: 0,
                    revision: 0,
                    quality_status: 'REALTIME',
                    quality_score: 1.0,

                    indicators: { ...indicatorValues }
                };
                
                this.activeCandles.set(sessionKey, newState);
                onUpdate(newState);
            });

            this.activeSessions.set(sessionKey, { chart, studies });
            logger.info(`Started TV Chart Session with Studies for ${symbol} ${timeframe}`);
        }
    }

    public unsubscribe(symbol: string, timeframe: string): void {
        const sessionKey = `${symbol}_${timeframe}`;
        const active = this.activeSessions.get(sessionKey);
        
        if (active) {
            if (active.studies) {
                for (const study of active.studies) {
                    try { study.remove(); } catch (e) {}
                }
            }
            if (active.chart) {
                try { active.chart.delete(); } catch (e) {}
            }
            this.activeSessions.delete(sessionKey);
            this.activeCandles.delete(sessionKey);
            this.subscriptionConfigs.delete(sessionKey);
            logger.info(`Stopped TV Chart Session for ${symbol} ${timeframe}`);
        }
    }
}
