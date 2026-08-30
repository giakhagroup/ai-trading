import { TradingViewProvider, ConnectionState } from './TradingViewProvider';
import { SymbolResolutionRegistry, SymbolState } from '../core/SymbolResolutionRegistry';
import { TradingViewErrorClassifier } from '../core/TradingViewErrorClassifier';
import { BackoffPolicy } from '../core/BackoffPolicy';
import assert from 'assert';

// Fake WebSocket Client
class FakeTVClient {
    private errCallback: Function | null = null;
    private dcCallback: Function | null = null;
    
    public Session = {
        Chart: class {
            public market: string = '';
            private updateCb: Function | null = null;
            private errCb: Function | null = null;
            
            setMarket(symbol: string, options: any) {
                this.market = symbol;
            }
            onUpdate(cb: Function) {
                this.updateCb = cb;
            }
            onError(cb: Function) {
                this.errCb = cb;
            }
            delete() {}
            
            // Test Helpers
            triggerError(...args: any[]) {
                if (this.errCb) this.errCb(...args);
            }
        }
    };

    onError(cb: Function) { this.errCallback = cb; }
    onDisconnected(cb: Function) { this.dcCallback = cb; }
    end() {
        if (this.dcCallback) this.dcCallback();
    }
}

async function sleep(ms: number) {
    return new Promise(res => setTimeout(res, ms));
}

async function runIntegrationTest() {
    console.log('Running TradingViewProvider Integration Test...');
    
    let fakeClientInstance: FakeTVClient;
    const wsFactory = () => {
        fakeClientInstance = new FakeTVClient();
        return fakeClientInstance;
    };

    const registry = new SymbolResolutionRegistry({ quarantineTTLMs: 5000 });
    const provider = new TradingViewProvider({
        registry,
        wsClientFactory: wsFactory,
        backoffPolicy: new BackoffPolicy({ baseDelayMs: 100, maxDelayMs: 1000, jitterFactor: 0 })
    });

    // 1. Connect
    await provider.connect();
    
    // 2. Subscribe to FPT (Valid) and BIV (Invalid)
    let fptUpdates = 0;
    await provider.subscribe('HOSE:FPT', '1H', () => { fptUpdates++; });
    await provider.subscribe('HOSE:BIV', '1H', () => {});
    
    assert.strictEqual(provider.getMetrics().active_symbols, 2);
    
    // 3. Simulate Invalid Symbol Error for BIV
    const sessions = (provider as any).activeSessions;
    const bivChart = sessions.get('HOSE:BIV_1H').chart;
    bivChart.triggerError('(ser_1) Symbol error:', 'invalid symbol');
    
    assert.strictEqual(registry.isQuarantined('HOSE:BIV'), true, 'BIV should be quarantined');
    assert.strictEqual(provider.getMetrics().active_sessions, 1, 'BIV session should be cleaned up immediately');

    // 4. Simulate Socket Disconnect
    fakeClientInstance!.end();
    
    // Should transition to RECONNECTING
    assert.ok(
        (provider as any).state === ConnectionState.RECONNECTING || (provider as any).state === ConnectionState.RESTORING,
        'Should be reconnecting or restoring'
    );
    
    // 5. Wait for Reconnect & Restore phase
    await sleep(800); // 100ms backoff + 500ms stagger + some execution time
    
    // After restore, FPT should be active, BIV should be skipped
    assert.strictEqual((provider as any).state, ConnectionState.CONNECTED);
    assert.strictEqual(provider.getMetrics().active_sessions, 1, 'Only FPT should be restored');
    assert.strictEqual(registry.isQuarantined('HOSE:BIV'), true);
    
    // 6. Cleanup
    await provider.disconnect();
    console.log('TradingViewProvider Integration Test Passed.');
}

runIntegrationTest().catch(err => {
    console.error('TradingViewProvider Integration Test Failed:', err);
    process.exit(1);
});
