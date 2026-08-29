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

    // Example implementation of a subscribe method for internal use by Aggregator
    public subscribe(symbol: string, timeframe: string, onUpdate: (candle: CanonicalCandle) => void): void {
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

            chart.onUpdate(() => {
                if (!chart.periods[0]) return;
                const tvCandle = chart.periods[0];
                
                // V2.0-012: Map to CanonicalCandle
                const canonical: CanonicalCandle = {
                    event_id: `${symbol}-${tvCandle.time}`,
                    provider: this.name,
                    provider_symbol: symbol,
                    internal_symbol: symbol, // In reality, this requires mapping logic
                    exchange: 'UNKNOWN',
                    asset_class: 'UNKNOWN',
                    currency: 'USD',
                    timezone: 'UTC',
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
                    
                    is_closed: false, // In reality, we need to determine if candle just closed
                    sequence: 0,
                    revision: 0,
                    quality_status: 'REALTIME',
                    quality_score: 1.0
                };
                
                onUpdate(canonical);
            });

            this.activeSessions.set(sessionKey, chart);
            logger.info(`Started TV Chart Session for ${symbol} ${timeframe}`);
        }
    }

    public unsubscribe(symbol: string, timeframe: string): void {
        const sessionKey = `${symbol}_${timeframe}`;
        const session = this.activeSessions.get(sessionKey);
        
        if (session) {
            // Depending on library, you may need to delete the session properly
            session.delete();
            this.activeSessions.delete(sessionKey);
            logger.info(`Stopped TV Chart Session for ${symbol} ${timeframe}`);
        }
    }
}
