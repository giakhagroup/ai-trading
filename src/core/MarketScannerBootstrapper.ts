import fs from 'fs';
import path from 'path';
import pino from 'pino';
import { SubscriptionAggregator } from './SubscriptionAggregator';
import { QuantBridge } from './QuantBridge';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

export class MarketScannerBootstrapper {
    private aggregator: SubscriptionAggregator;
    private bridge: QuantBridge;
    private universe: string[] = [];

    constructor(aggregator: SubscriptionAggregator, bridge: QuantBridge) {
        this.aggregator = aggregator;
        this.bridge = bridge;
    }

    public async loadUniverse(filePath: string): Promise<void> {
        try {
            const absolutePath = path.resolve(process.cwd(), filePath);
            if (!fs.existsSync(absolutePath)) {
                logger.warn(`Universe file not found at ${absolutePath}, skipping.`);
                return;
            }
            const data = fs.readFileSync(absolutePath, 'utf-8');
            const parsed = JSON.parse(data);
            this.universe = parsed.symbols || [];
            logger.info(`Loaded ${this.universe.length} symbols from ${filePath}`);
        } catch (e: any) {
            logger.error(`Failed to load universe: ${e.message}`);
        }
    }

    public async start(timeframe: string = '1H'): Promise<void> {
        if (this.universe.length === 0) {
            logger.warn('Universe is empty. Bootstrapper will not start any subscriptions.');
            return;
        }

        logger.info('Starting staggered subscriptions for Market Scanner...');

        for (const symbol of this.universe) {
            try {
                await this.aggregator.subscribe(symbol, timeframe, (candle) => {
                    this.bridge.forwardCandle(candle);
                });
                
                logger.info(`Subscribed to ${symbol} [${timeframe}]`);
                
                // PACING: Wait 500ms before subscribing to the next symbol
                // This prevents TradingView client from sending a burst of 30 WS messages 
                // at the exact same millisecond, which could trigger rate limits.
                await new Promise(resolve => setTimeout(resolve, 500));
            } catch (e: any) {
                logger.error(`Failed to subscribe to ${symbol}: ${e.message}`);
            }
        }
        
        logger.info('Market Scanner Bootstrapper finished initialization.');
    }
}
