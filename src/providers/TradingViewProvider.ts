import TradingView from '@mathieuc/tradingview';
import pino from 'pino';
import { MarketDataProvider, ProviderCapabilities, CanonicalCandle } from '../core/interfaces';
import { SymbolResolutionRegistry, SymbolState } from '../core/SymbolResolutionRegistry';
import { TradingViewErrorClassifier, ErrorCategory } from '../core/TradingViewErrorClassifier';
import { BackoffPolicy } from '../core/BackoffPolicy';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

export enum ConnectionState {
    DISCONNECTED = 'DISCONNECTED',
    CONNECTING = 'CONNECTING',
    CONNECTED = 'CONNECTED',
    RECONNECTING = 'RECONNECTING',
    RESTORING = 'RESTORING'
}

interface SubscriptionConfig {
    symbol: string;
    timeframe: string;
    onUpdate: (candle: CanonicalCandle) => void;
    indicatorsToAttach: string[];
}

export interface ProviderMetrics {
    reconnects: number;
    reconnect_failures: number;
    active_sessions: number;
    active_symbols: number;
    subscription_failures: number;
    invalid_symbols: number;
    quarantined_symbols: number;
    events_received: number;
    events_emitted: number;
    duplicates: number;
    out_of_order_events: number;
}

export interface TradingViewProviderOptions {
    registry?: SymbolResolutionRegistry;
    errorClassifier?: TradingViewErrorClassifier;
    backoffPolicy?: BackoffPolicy;
    wsClientFactory?: () => any; // For test injection
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
    private state: ConnectionState = ConnectionState.DISCONNECTED;
    
    private activeSessions: Map<string, any> = new Map();
    private activeCandles: Map<string, CanonicalCandle> = new Map();
    private subscriptionConfigs: Map<string, SubscriptionConfig> = new Map();

    private registry: SymbolResolutionRegistry;
    private errorClassifier: TradingViewErrorClassifier;
    private backoffPolicy: BackoffPolicy;
    private wsClientFactory: () => any;

    private reconnectAttempt: number = 0;
    
    private metrics: ProviderMetrics = {
        reconnects: 0,
        reconnect_failures: 0,
        active_sessions: 0,
        active_symbols: 0,
        subscription_failures: 0,
        invalid_symbols: 0,
        quarantined_symbols: 0,
        events_received: 0,
        events_emitted: 0,
        duplicates: 0,
        out_of_order_events: 0
    };

    constructor(options?: TradingViewProviderOptions) {
        this.registry = options?.registry || new SymbolResolutionRegistry();
        this.errorClassifier = options?.errorClassifier || new TradingViewErrorClassifier();
        this.backoffPolicy = options?.backoffPolicy || new BackoffPolicy();
        this.wsClientFactory = options?.wsClientFactory || (() => new TradingView.Client());
    }

    public getMetrics(): ProviderMetrics {
        this.metrics.active_sessions = this.activeSessions.size;
        this.metrics.active_symbols = new Set(Array.from(this.subscriptionConfigs.values()).map(c => c.symbol)).size;
        this.metrics.quarantined_symbols = this.registry.getQuarantinedCount();
        return { ...this.metrics };
    }

    public async connect(): Promise<void> {
        if (this.state === ConnectionState.CONNECTED || this.state === ConnectionState.CONNECTING) return;
        
        this.state = ConnectionState.CONNECTING;
        
        return new Promise((resolve, reject) => {
            try {
                this.client = this.wsClientFactory();
                
                this.client.onError((err: any) => {
                    logger.error({ err }, 'TradingView Client Socket Error');
                });
                
                this.client.onDisconnected(() => {
                    logger.warn('TradingView Socket Disconnected.');
                    if (this.state !== ConnectionState.DISCONNECTED) {
                        this.handleReconnect();
                    }
                });
                
                this.state = ConnectionState.CONNECTED;
                this.reconnectAttempt = 0;
                logger.info('TradingView Provider connected.');
                resolve();
            } catch (err) {
                this.state = ConnectionState.DISCONNECTED;
                logger.error({ err }, 'Failed to connect to TradingView');
                reject(err);
            }
        });
    }
    
    private async handleReconnect() {
        if (this.state === ConnectionState.RECONNECTING || this.state === ConnectionState.RESTORING) return;
        this.state = ConnectionState.RECONNECTING;
        this.metrics.reconnects++;

        const delay = this.backoffPolicy.calculateDelay(this.reconnectAttempt);
        logger.info(`Scheduling reconnect attempt ${this.reconnectAttempt + 1} in ${delay}ms...`);
        
        setTimeout(async () => {
            try {
                // 1. Socket Reconnect Phase
                await this.connect();
                
                // 2. Restoration Phase
                this.state = ConnectionState.RESTORING;
                await this.restoreSubscriptions();
                
                this.state = ConnectionState.CONNECTED;
                logger.info('Reconnect and restoration complete.');
            } catch (e) {
                logger.error('Failed to reconnect.');
                this.metrics.reconnect_failures++;
                this.reconnectAttempt++;
                this.state = ConnectionState.DISCONNECTED;
                this.handleReconnect();
            }
        }, delay);
    }

    private async restoreSubscriptions() {
        const configs = Array.from(this.subscriptionConfigs.values());
        this.activeSessions.clear();
        
        for (const config of configs) {
            if (this.registry.isQuarantined(config.symbol)) {
                logger.warn(`Skipping quarantined symbol ${config.symbol} during restoration.`);
                continue;
            }
            try {
                await this.subscribe(config.symbol, config.timeframe, config.onUpdate, config.indicatorsToAttach, true);
                // Stagger restoration
                await new Promise(res => setTimeout(res, 500));
            } catch (err) {
                logger.error(`Failed to restore subscription for ${config.symbol}`);
                this.metrics.subscription_failures++;
            }
        }
    }

    public async disconnect(): Promise<void> {
        this.state = ConnectionState.DISCONNECTED;
        if (this.client) {
            this.client.end();
        }
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
        if (this.state === ConnectionState.DISCONNECTED) {
            throw new Error('Provider is not connected');
        }

        const sessionKey = `${symbol}_${timeframe}`;
        
        if (!isReconnect) {
            this.subscriptionConfigs.set(sessionKey, { symbol, timeframe, onUpdate, indicatorsToAttach });
        }

        if (this.registry.isQuarantined(symbol)) {
            logger.warn(`Cannot subscribe to ${symbol}, it is QUARANTINED.`);
            return;
        }

        if (!this.activeSessions.has(sessionKey)) {
            const chart = new this.client.Session.Chart();
            this.registry.markState(symbol, SymbolState.RESOLVING);
            chart.setMarket(symbol, { timeframe });
            
            chart.onError((...err: any[]) => {
                const category = this.errorClassifier.classifyChartError(err);
                if (category === ErrorCategory.INVALID_SYMBOL) {
                    this.registry.markState(symbol, SymbolState.QUARANTINED);
                    this.metrics.invalid_symbols++;
                    logger.error(`Symbol ${symbol} classified as INVALID_SYMBOL and QUARANTINED.`);
                    // Clean up invalid session immediately
                    this.unsubscribeInternal(sessionKey, false); 
                } else if (category === ErrorCategory.CONNECTION) {
                    logger.error({ err }, `Connection error on chart ${symbol}`);
                    // Do NOT mark as invalid. The main client disconnect handler will deal with socket issues.
                } else {
                    logger.warn({ err }, `Transient/Unknown error on chart ${symbol}`);
                }
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
                    // logger.info(`Attached indicator study ${indicatorName} to ${symbol}`);
                } catch (e: any) {
                    logger.warn(`Could not attach indicator ${indicatorName} to ${symbol}: ${e.message}`);
                }
            }

            chart.onUpdate(() => {
                if (this.registry.getState(symbol) !== SymbolState.ACTIVE) {
                    this.registry.markState(symbol, SymbolState.ACTIVE);
                }
                
                if (!chart.periods[0]) return;
                const tvCandle = chart.periods[0];
                const tickTime = tvCandle.time * 1000;
                
                this.metrics.events_received++;
                const activeState = this.activeCandles.get(sessionKey);
                
                // QUANT ROLLOVER & DISCARD LOGIC
                if (activeState) {
                    if (tickTime < activeState.source_timestamp) {
                        this.metrics.out_of_order_events++;
                        return; // DISCARD out-of-order data
                    }
                    
                    if (tickTime > activeState.source_timestamp) {
                        // ROLLOVER
                        const closedCandle = { ...activeState, is_closed: true };
                        this.metrics.events_emitted++;
                        onUpdate(closedCandle);
                        
                        // Fallthrough to create new state
                    } else {
                        // UPDATE: Same timestamp
                        // Heuristic for duplicate (if exact same OHLCV values arrived again)
                        if (tvCandle.close === activeState.close && tvCandle.volume === activeState.volume) {
                            // might be duplicate update with no real change, but let's just count it
                        }
                        
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
                        this.metrics.events_emitted++;
                        onUpdate(updatedState);
                        return;
                    }
                }
                
                // NEW CANDLE
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
                this.metrics.events_emitted++;
                onUpdate(newState);
            });

            this.activeSessions.set(sessionKey, { chart, studies });
            logger.info(`Started TV Chart Session for ${symbol} ${timeframe}`);
        }
    }

    public unsubscribe(symbol: string, timeframe: string): void {
        const sessionKey = `${symbol}_${timeframe}`;
        this.unsubscribeInternal(sessionKey, true);
    }
    
    private unsubscribeInternal(sessionKey: string, removeFromConfig: boolean) {
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
            if (removeFromConfig) {
                this.subscriptionConfigs.delete(sessionKey);
            }
            logger.info(`Stopped TV Chart Session for ${sessionKey}`);
        }
    }
}
