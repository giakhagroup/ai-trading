import { SymbolResolutionRegistry, SymbolState } from './SymbolResolutionRegistry';
import assert from 'assert';

async function runTests() {
    console.log('Running SymbolResolutionRegistry Tests...');
    
    // Test 1: Basic State Management
    const registry = new SymbolResolutionRegistry({ quarantineTTLMs: 100 });
    assert.strictEqual(registry.getState('FPT'), SymbolState.UNKNOWN);
    
    registry.markState('FPT', SymbolState.RESOLVING);
    assert.strictEqual(registry.getState('FPT'), SymbolState.RESOLVING);
    
    registry.markState('FPT', SymbolState.ACTIVE);
    assert.strictEqual(registry.getState('FPT'), SymbolState.ACTIVE);
    
    // Test 2: Quarantine Logic
    registry.markState('BIV', SymbolState.QUARANTINED);
    assert.strictEqual(registry.isQuarantined('BIV'), true);
    assert.strictEqual(registry.getQuarantinedCount(), 1);
    
    // Test 3: TTL Reversion
    await new Promise(res => setTimeout(res, 150));
    assert.strictEqual(registry.isQuarantined('BIV'), false, 'Should have reverted to UNKNOWN after TTL');
    assert.strictEqual(registry.getState('BIV'), SymbolState.UNKNOWN);
    assert.strictEqual(registry.getQuarantinedCount(), 0);

    console.log('SymbolResolutionRegistry Tests Passed.');
}

runTests().catch(err => {
    console.error('SymbolResolutionRegistry Tests Failed:', err);
    process.exit(1);
});
