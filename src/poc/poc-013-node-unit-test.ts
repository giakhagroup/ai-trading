import assert from 'assert';
import { SubscriptionAggregator } from '../core/SubscriptionAggregator';
import { CanonicalCandle, MarketDataProvider, ProviderCapabilities } from '../core/interfaces';
import { SessionType } from '../core/types';

// Mock Provider for testing
class MockMarketDataProvider implements MarketDataProvider {
    public name = 'MockProvider';
    public capabilities: ProviderCapabilities = {
        realtime: true,
        historical: true,
        quotes: true,
        ohlcv: true,
        multiSymbol: true,
        multiTimeframe: true,
        builtInIndicators: true,
        pineIndicators: false,
        replay: true,
        screener: false
    };

    public connected = false;
    public async connect(): Promise<void> {
        this.connected = true;
    }

    async disconnect(): Promise<void> {
        this.connected = false;
    }
    
    async subscribe(symbol: string, timeframe: string, onUpdate: (candle: CanonicalCandle) => void): Promise<void> {
        // Mock subscribe
    }
    
    unsubscribe(symbol: string, timeframe: string): void {
        // Mock unsubscribe
    }
}

async function runNodeUnitTests() {
    console.log('🧪 Starting Node.js Unit Tests for Core Components...\n');
    let passed = 0;
    let failed = 0;

    function test(name: string, fn: () => void | Promise<void>) {
        try {
            fn();
            console.log(`  ✅ PASS: ${name}`);
            passed++;
        } catch (e: any) {
            console.error(`  ❌ FAIL: ${name} -> ${e.message}`);
            failed++;
        }
    }

    // 1. Test Aggregator Multi-Subscriber Single Channel
    test('Aggregator correctly registers multiple subscribers on the same symbol/timeframe', async () => {
        const mock = new MockMarketDataProvider();
        const aggregator = new SubscriptionAggregator(mock);

        let countA = 0;
        let countB = 0;

        const cbA = (candle: CanonicalCandle) => { countA++; };
        const cbB = (candle: CanonicalCandle) => { countB++; };

        await aggregator.subscribe('HOSE:FPT', '1', cbA);
        await aggregator.subscribe('HOSE:FPT', '1', cbB);

        const dummyCandle: CanonicalCandle = {
            event_id: 'evt_1',
            provider: 'Mock',
            provider_symbol: 'HOSE:FPT',
            internal_symbol: 'HOSE:FPT',
            exchange: 'HOSE',
            asset_class: 'STOCK',
            currency: 'VND',
            timezone: 'Asia/Ho_Chi_Minh',
            timeframe: '1',
            source_timestamp: 1000,
            event_timestamp: 1000,
            received_at: 1000,
            processed_at: 1000,
            open: 70000,
            high: 71000,
            low: 69000,
            close: 70500,
            volume: 1000,
            is_closed: true,
            sequence: 1,
            revision: 0,
            quality_status: 'REALTIME',
            quality_score: 1.0,
            session_type: SessionType.CONTINUOUS,
            indicators: { RSI: 30 }
        };

        // Dispatch data
        aggregator.onDataReceived('HOSE:FPT', '1', dummyCandle);

        assert.strictEqual(countA, 1, 'Subscriber A should receive 1 event');
        assert.strictEqual(countB, 1, 'Subscriber B should receive 1 event');

        // Unsubscribe A
        await aggregator.unsubscribe('HOSE:FPT', '1', cbA);
        aggregator.onDataReceived('HOSE:FPT', '1', dummyCandle);

        assert.strictEqual(countA, 1, 'Subscriber A should not receive further events');
        assert.strictEqual(countB, 2, 'Subscriber B should receive the 2nd event');
    });

    // 2. Test Key generation
    test('Subscription key formatting is deterministic', () => {
        const mock = new MockMarketDataProvider();
        const aggregator = new SubscriptionAggregator(mock);
        const key = aggregator.getSubscriptionKey('HOSE:MWG', '5');
        assert.strictEqual(key, 'HOSE:MWG_5');
    });

    console.log(`\n--------------------------------------------------`);
    console.log(`Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
    console.log(`--------------------------------------------------\n`);

    if (failed > 0) process.exit(1);
}

runNodeUnitTests().catch(console.error);
