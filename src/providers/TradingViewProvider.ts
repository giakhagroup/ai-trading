import TradingView from '@mathieuc/tradingview';
import pino from 'pino';
import { MarketDataProvider, ProviderCapabilities, CanonicalCandle } from '../core/interfaces';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

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
    private activeSessions: Map<string, any> = new Map();

    public async connect(): Promise<void> {
        if (this.isConnected) return;
        
        return new Promise((resolve, reject) => {
            try {
                this.client = new TradingView.Client();
                
                this.client.onError((err: any) => {
                    logger.error({ err }, 'TradingView Client Error');
                });
                
                this.isConnected = true;
                logger.info('TradingView Provider connected.');
                resolve();
            } catch (err) {
                logger.error({ err }, 'Failed to connect to TradingView');
                reject(err);
            }
        });
    }

    public async disconnect(): Promise<void> {
        if (!this.isConnected || !this.client) return;
        this.client.end();
        this.isConnected = false;
        this.activeSessions.clear();
        logger.info('TradingView Provider disconnected.');
    }

    // Subscribe with optional indicator study attachments (e.g. RSI, MACD)
    public async subscribe(
        symbol: string,
        timeframe: string,
        onUpdate: (candle: CanonicalCandle) => void,
        indicatorsToAttach: string[] = ['STD;Relative_Strength_Index']
    ): Promise<void> {
        if (!this.isConnected) {
            throw new Error('Provider is not connected');
        }

        const sessionKey = `${symbol}_${timeframe}`;
        if (!this.activeSessions.has(sessionKey)) {
            const chart = new this.client.Session.Chart();
            chart.setMarket(symbol, { timeframe });
            
            chart.onError((...err: any[]) => {
                logger.error({ err }, `Chart Error for ${symbol}`);
            });

            // Store attached studies
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
                
                // V2.0-012: Map to CanonicalCandle
                const canonical: CanonicalCandle = {
                    event_id: `${symbol}-${tvCandle.time}`,
                    provider: this.name,
                    provider_symbol: symbol,
                    internal_symbol: symbol,
                    exchange: symbol.split(':')[0] || 'UNKNOWN',
                    asset_class: 'STOCK',
                    currency: 'VND',
                    timezone: 'Asia/Ho_Chi_Minh',
                    timeframe: timeframe,
                    
                    source_timestamp: tvCandle.time * 1000,
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

                    // Attached indicators snapshot
                    indicators: { ...indicatorValues }
                };
                
                onUpdate(canonical);
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
            logger.info(`Stopped TV Chart Session for ${symbol} ${timeframe}`);
        }
    }
}
