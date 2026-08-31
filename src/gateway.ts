import fs from 'fs';
import path from 'path';
import pino from 'pino';
import { TradingViewProvider } from './providers/TradingViewProvider';
import { QuantBridge } from './core/QuantBridge';
import { SymbolResolutionRegistry } from './core/SymbolResolutionRegistry';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

async function runGateway() {
    console.log('==================================================');
    console.log('🚀 Starting Node.js Gateway (Phase 5A - VN30 Scanner)');
    console.log('==================================================');

    // 1. Check Python Backend
    const bridge = new QuantBridge({ pythonEngineUrl: 'http://127.0.0.1:8000' });
    const isHealthy = await bridge.checkHealth();
    if (!isHealthy) {
        logger.error('❌ Python FastAPI is not running or unreachable at http://127.0.0.1:8000.');
        logger.error('Please make sure python/api/main.py is started.');
        process.exit(1);
    }
    logger.info('✅ Connected to Python Backend.');

    // 2. Load VN30 Universe
    const vn30Path = path.join(__dirname, '../data/universes/vn30_2026.json');
    let vn30Symbols: string[] = [];
    try {
        const rawData = fs.readFileSync(vn30Path, 'utf-8');
        const parsed = JSON.parse(rawData);
        vn30Symbols = parsed.symbols || [];
        logger.info(`✅ Loaded ${vn30Symbols.length} symbols from VN30 Universe.`);
    } catch (e: any) {
        logger.error(`❌ Failed to load VN30 Universe: ${e.message}`);
        process.exit(1);
    }

    // 3. Connect to TradingView Provider
    const registry = new SymbolResolutionRegistry({ quarantineTTLMs: 300000 });
    const provider = new TradingViewProvider({ registry });
    await provider.connect();

    // 4. Subscribe to VN30 Universe
    const timeframes = ['15', '60'];
    let delay = 0;

    for (const symbol of vn30Symbols) {
        for (const tf of timeframes) {
            // Stagger subscriptions to avoid hitting rate limits or overwhelming socket
            delay += 50; 
            setTimeout(async () => {
                logger.info(`📡 Subscribing to ${symbol} (${tf}m)...`);
                await provider.subscribe(
                    symbol,
                    tf,
                    async (candle) => {
                        // Forward closed candles or all candles? 
                        // Phase 5A: "Scanner phải event-driven + coalescing và chỉ trigger trên is_closed=true"
                        // But we must forward all to maintain indicator accuracy!
                        // The Python side will handle the "only trigger on is_closed=true" logic for the scanner.
                        await bridge.forwardCandle(candle);
                    }
                );
            }, delay);
        }
    }
}

runGateway().catch((err) => {
    logger.error({ err }, 'Gateway crashed');
    process.exit(1);
});
