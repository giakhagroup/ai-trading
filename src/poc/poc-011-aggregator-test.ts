import { SubscriptionAggregator } from '../core/SubscriptionAggregator';
import { TradingViewProvider } from '../providers/TradingViewProvider';
import { CanonicalCandle } from '../core/interfaces';

async function testAggregator() {
    console.log('--- Testing Subscription Aggregator ---');
    const provider = new TradingViewProvider();
    
    // Quick mock to link provider's subscribe logic to the aggregator
    // In a real implementation, the aggregator should wrap the provider's subscribe method tightly.
    // For this POC, we'll patch the aggregator to call the provider directly.
    const aggregator = new SubscriptionAggregator(provider);
    
    // Monkey patch the TODOs for this test
    const originalSubscribe = aggregator.subscribe.bind(aggregator);
    aggregator.subscribe = async (symbol: string, timeframe: string, callback: any) => {
        const key = aggregator.getSubscriptionKey(symbol, timeframe);
        const isNew = !(aggregator as any).subscribers.has(key);
        
        await originalSubscribe(symbol, timeframe, callback);
        
        if (isNew) {
            console.log(`[Aggregator] First subscriber for ${key}. Requesting from Provider...`);
            provider.subscribe(symbol, timeframe, (candle: CanonicalCandle) => {
                aggregator.onDataReceived(symbol, timeframe, candle);
            });
        } else {
            console.log(`[Aggregator] Reusing existing connection for ${key}.`);
        }
    };

    await provider.connect();

    console.log('\n1. User A subscribes to HOSE:FPT 1M');
    await aggregator.subscribe('HOSE:FPT', '1', (candle) => {
        console.log(`[User A] received update for FPT: Close=${candle.close}`);
    });

    setTimeout(async () => {
        console.log('\n2. User B subscribes to HOSE:FPT 1M (Should reuse connection)');
        await aggregator.subscribe('HOSE:FPT', '1', (candle) => {
            console.log(`[User B] received update for FPT: Close=${candle.close}`);
        });
    }, 2000);

    setTimeout(async () => {
        console.log('\n3. User C subscribes to BINANCE:BTCUSDT 1M (Should create new connection)');
        await aggregator.subscribe('BINANCE:BTCUSDT', '1', (candle) => {
            console.log(`[User C] received update for BTCUSDT: Close=${candle.close}`);
        });
    }, 4000);

    setTimeout(async () => {
        console.log('\n--- Test Finished ---');
        await provider.disconnect();
        process.exit(0);
    }, 8000);
}

testAggregator().catch(console.error);
