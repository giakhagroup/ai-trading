import { TradingViewErrorClassifier, ErrorCategory } from './TradingViewErrorClassifier';
import assert from 'assert';

function runTests() {
    console.log('Running TradingViewErrorClassifier Tests...');
    const classifier = new TradingViewErrorClassifier();

    // Test 1: INVALID_SYMBOL
    assert.strictEqual(
        classifier.classifyChartError(['(ser_1) Symbol error:', 'invalid symbol']),
        ErrorCategory.INVALID_SYMBOL
    );
    assert.strictEqual(
        classifier.classifyChartError(['unknown symbol HOSE:ABC']),
        ErrorCategory.INVALID_SYMBOL
    );

    // Test 2: TRANSIENT
    assert.strictEqual(
        classifier.classifyChartError(['Series error:', 'resolve error']),
        ErrorCategory.TRANSIENT
    );

    // Test 3: CONNECTION
    assert.strictEqual(
        classifier.classifyChartError(['WebSocket disconnected']),
        ErrorCategory.CONNECTION
    );
    assert.strictEqual(
        classifier.classifyChartError(['network timeout']),
        ErrorCategory.CONNECTION
    );

    // Test 4: UNKNOWN
    assert.strictEqual(
        classifier.classifyChartError(['Some random error message']),
        ErrorCategory.UNKNOWN
    );

    console.log('TradingViewErrorClassifier Tests Passed.');
}

runTests();
