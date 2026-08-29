import { TradingViewProvider } from '../providers/TradingViewProvider';
import { QuantBridge } from '../core/QuantBridge';
import { CanonicalCandle } from '../core/interfaces';

async function runHybridStream() {
    console.log('==================================================');
    console.log('🚀 Starting Hybrid Integration Test (Node.js + Python)');
    console.log('==================================================');

    const bridge = new QuantBridge({ pythonEngineUrl: 'http://127.0.0.1:8000' });
    const isHealthy = await bridge.checkHealth();
    
    if (!isHealthy) {
        console.error('❌ Python Quant Engine is not running or unreachable at http://127.0.0.1:8000.');
        console.error('Please make sure python/main.py is started.');
        process.exit(1);
    }
    console.log('✅ Connected to Python Quant & Risk Engine.');

    const provider = new TradingViewProvider();
    await provider.connect();

    const symbol = 'HOSE:FPT';
    const timeframe = '1';
    console.log(`\n📡 Subscribing to ${symbol} (${timeframe}m) with Attached RSI Study...`);

    let updateCount = 0;

    await provider.subscribe(
        symbol,
        timeframe,
        async (candle: CanonicalCandle) => {
            updateCount++;
            console.log(`\n[Node.js Event #${updateCount}] ${candle.internal_symbol} Close=${candle.close} RSI=${candle.indicators?.RSI ?? 'calc...'}`);
            
            // Forward to Python Quant Engine
            const response = await bridge.forwardCandle(candle);
            if (response) {
                if (response.candidates?.length > 0) {
                    console.log(`  -> 💡 Python Candidates: ${response.candidates.length}`);
                }
                if (response.validated?.length > 0) {
                    console.log(`  -> 🎯 Python VALIDATED SIGNALS: ${JSON.stringify(response.validated)}`);
                }
                if (response.rejected?.length > 0) {
                    console.log(`  -> ⚠️ Python REJECTED SIGNALS: ${JSON.stringify(response.rejected)}`);
                }
            }
        },
        ['STD;Relative_Strength_Index']
    );

    // Run for 15 seconds then finish
    setTimeout(async () => {
        console.log('\n==================================================');
        console.log('🏁 Integration Stream Test Complete. Disconnecting...');
        console.log('==================================================');
        await provider.disconnect();
        process.exit(0);
    }, 15000);
}

runHybridStream().catch(console.error);
