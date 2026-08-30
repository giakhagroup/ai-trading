import { TradingViewProvider, ConnectionState } from '../providers/TradingViewProvider';
import { SymbolResolutionRegistry, SymbolState } from '../core/SymbolResolutionRegistry';
import { TradingViewErrorClassifier } from '../core/TradingViewErrorClassifier';
import { BackoffPolicy } from '../core/BackoffPolicy';
import assert from 'assert';

async function sleep(ms: number) {
    return new Promise(res => setTimeout(res, ms));
}

async function runResilienceE2E() {
    console.log('=== Starting Limited E2E Resilience Test ===');

    const registry = new SymbolResolutionRegistry({ quarantineTTLMs: 300000 });
    const provider = new TradingViewProvider({
        registry,
        errorClassifier: new TradingViewErrorClassifier(),
        backoffPolicy: new BackoffPolicy({ baseDelayMs: 100, maxDelayMs: 2000 }) // Fast backoff for test
    });

    try {
        await provider.connect();
        console.log('Connected to TradingView.');

        let fptEvents = 0;
        await provider.subscribe('HOSE:FPT', '1H', () => { fptEvents++; });
        console.log('Subscribed to HOSE:FPT');

        // BIV is known to trigger "invalid symbol" and "resolve error"
        await provider.subscribe('HOSE:BIV', '1H', () => { });
        console.log('Subscribed to HOSE:BIV (expected INVALID_SYMBOL)');

        // Wait for connections to establish and errors to return
        console.log('Waiting 5 seconds for TV to respond...');
        await sleep(5000);

        const metrics1 = provider.getMetrics();
        console.log('Metrics After Init:', metrics1);

        // Verifications
        assert.strictEqual(registry.isQuarantined('HOSE:BIV'), true, 'BIV should be QUARANTINED');
        assert.strictEqual(registry.getState('HOSE:FPT'), SymbolState.ACTIVE, 'FPT should be ACTIVE');
        assert.ok(fptEvents > 0 || (provider as any).state === ConnectionState.CONNECTED, 'FPT should be receiving events or at least be CONNECTED');
        assert.strictEqual((provider as any).state, ConnectionState.CONNECTED, 'Socket MUST survive invalid symbol');

        console.log('✅ Invalid symbol isolated. Socket survived.');

        // Force a network disconnect
        console.log('Forcing network disconnect...');
        (provider as any).client.end(); // Trigger natural disconnect hook

        // Wait for Reconnect + Restore
        console.log('Waiting 5 seconds for reconnect & restore...');
        await sleep(5000);

        const metrics2 = provider.getMetrics();
        console.log('Metrics After Reconnect:', metrics2);

        assert.strictEqual((provider as any).state, ConnectionState.CONNECTED, 'Provider should have reconnected successfully');
        assert.strictEqual(registry.isQuarantined('HOSE:BIV'), true, 'BIV should still be QUARANTINED');

        // Active sessions should only be 1 (FPT) because BIV was skipped during RESTORING
        assert.strictEqual(metrics2.active_sessions, 1, 'Only FPT should be active');
        assert.ok(metrics2.reconnects > 0, 'Should have triggered reconnect logic');

        console.log('✅ Reconnect successful. FPT restored. BIV skipped.');

        console.log('=== E2E Resilience Test Passed ===');
    } catch (err) {
        console.error('E2E Resilience Test Failed:', err);
        process.exit(1);
    } finally {
        await provider.disconnect();
    }
}

runResilienceE2E();
