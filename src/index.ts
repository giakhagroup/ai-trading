import { TradingViewProvider } from './providers/TradingViewProvider';
import { SubscriptionAggregator } from './core/SubscriptionAggregator';
import { QuantBridge } from './core/QuantBridge';
import { MarketScannerBootstrapper } from './core/MarketScannerBootstrapper';
import pino from 'pino';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

async function main() {
    logger.info('Starting Node.js Gateway for AI Trading...');

    // 1. Initialize Python Quant Bridge
    const bridge = new QuantBridge({
        pythonEngineUrl: process.env.QUANT_ENGINE_URL || 'http://127.0.0.1:8000',
        timeoutMs: 5000
    });

    const isHealthy = await bridge.checkHealth();
    if (!isHealthy) {
        logger.error('Python Quant Engine is not reachable. Ensure it is running at the configured URL.');
        // Depending on requirements, we could exit here, but we can also just keep trying to send events.
    } else {
        logger.info('Python Quant Engine is reachable.');
    }

    // 2. Initialize TradingView Provider
    const provider = new TradingViewProvider();
    
    // 3. Connect to Provider
    try {
        await provider.connect();
    } catch (e) {
        logger.error('Failed to connect to TradingView provider, shutting down...');
        process.exit(1);
    }

    // 4. Setup Aggregator
    const aggregator = new SubscriptionAggregator(provider);

    // 5. Initialize Bootstrapper
    const bootstrapper = new MarketScannerBootstrapper(aggregator, bridge);
    
    // Load Universe from data folder (path relative to CWD)
    const universePath = process.env.UNIVERSE_PATH || 'data/universes/vn30_2026.json';
    await bootstrapper.loadUniverse(universePath);

    // 6. Start Staggered Subscriptions for Market Scanner
    // Default timeframe is 1H. Can be overridden via env vars if needed.
    await bootstrapper.start('1H');

    logger.info('Gateway successfully initialized and running.');
    
    // Graceful Shutdown handling
    process.on('SIGINT', async () => {
        logger.info('Received SIGINT. Shutting down gracefully...');
        await provider.disconnect();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        logger.info('Received SIGTERM. Shutting down gracefully...');
        await provider.disconnect();
        process.exit(0);
    });
}

main().catch(err => {
    logger.fatal({ err }, 'Fatal error during Gateway startup');
    process.exit(1);
});
