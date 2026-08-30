import { BackoffPolicy } from './BackoffPolicy';
import assert from 'assert';

function runTests() {
    console.log('Running BackoffPolicy Tests...');
    
    // Deterministic test without jitter
    const policy = new BackoffPolicy({ baseDelayMs: 1000, maxDelayMs: 60000, factor: 2, jitterFactor: 0 });
    
    assert.strictEqual(policy.calculateDelay(0), 1000); // 1000 * 2^0
    assert.strictEqual(policy.calculateDelay(1), 2000); // 1000 * 2^1
    assert.strictEqual(policy.calculateDelay(2), 4000); // 1000 * 2^2
    assert.strictEqual(policy.calculateDelay(6), 60000); // 1000 * 2^6 = 64000 -> capped at 60000
    
    // Test with Jitter
    const jitterPolicy = new BackoffPolicy({ baseDelayMs: 1000, maxDelayMs: 60000, factor: 2, jitterFactor: 0.2 });
    const delay0 = jitterPolicy.calculateDelay(0);
    assert.ok(delay0 >= 800 && delay0 <= 1200, `Delay ${delay0} out of jitter bounds`);
    
    const delay6 = jitterPolicy.calculateDelay(6);
    assert.ok(delay6 >= 48000 && delay6 <= 60000, `Delay ${delay6} out of capped bounds`);

    // Deterministic RNG Test
    const deterministicRng = () => 0.5; // Always return 0.5 (middle of jitter variance)
    const deterministicPolicy = new BackoffPolicy({ baseDelayMs: 1000, maxDelayMs: 60000, factor: 2, jitterFactor: 0.2, rng: deterministicRng });
    // base = 1000. Jitter variance = 1000 * 0.2 = 200.
    // Jitter = (0.5 * 200 * 2) - 200 = (200) - 200 = 0.
    // Result should be exactly 1000.
    assert.strictEqual(deterministicPolicy.calculateDelay(0), 1000);
    
    // For max value RNG
    const maxRng = () => 0.9999999999999999;
    const maxPolicy = new BackoffPolicy({ baseDelayMs: 1000, factor: 2, jitterFactor: 0.2, rng: maxRng });
    // base = 1000. variance = 200.
    // jitter = (0.999999 * 400) - 200 = almost +200. Final = 1200
    assert.strictEqual(maxPolicy.calculateDelay(0), 1200); // Due to Math.floor and floating point precision

    console.log('BackoffPolicy Tests Passed.');
}

runTests();
