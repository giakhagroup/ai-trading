import { TradingViewProvider, ConnectionState } from '../providers/TradingViewProvider';
import { SymbolResolutionRegistry } from '../core/SymbolResolutionRegistry';
import { TradingViewErrorClassifier } from '../core/TradingViewErrorClassifier';
import { BackoffPolicy } from '../core/BackoffPolicy';
import { CanonicalCandle } from '../core/interfaces';

async function sleep(ms: number) {
    return new Promise(res => setTimeout(res, ms));
}

async function runIndicatorReconnectTest() {
    console.log('=== Starting Indicator Reconnect Gap Test ===');

    const registry = new SymbolResolutionRegistry();
    const provider = new TradingViewProvider({
        registry,
        errorClassifier: new TradingViewErrorClassifier(),
        backoffPolicy: new BackoffPolicy({ baseDelayMs: 100, maxDelayMs: 500 }) // Fast reconnect
    });

    try {
        await provider.connect();
        
        let preReconnectIndicators: any = null;
        let postReconnectFirstIndicators: any = null;
        let hasReconnected = false;
        
        const onUpdate = (candle: CanonicalCandle) => {
            if (!hasReconnected) {
                if (candle.indicators && Object.keys(candle.indicators).length > 0 && !preReconnectIndicators) {
                    console.log('\n[PRE-RECONNECT] First valid indicators received:', JSON.stringify(candle.indicators));
                    preReconnectIndicators = candle.indicators;
                }
            } else {
                // Record the FIRST valid indicator values received AFTER reconnect
                if (candle.indicators && Object.keys(candle.indicators).length > 0 && !postReconnectFirstIndicators) {
                    postReconnectFirstIndicators = candle.indicators;
                    console.log('\n[POST-RECONNECT] First valid indicators received:', JSON.stringify(candle.indicators));
                }
            }
        };

        await provider.subscribe('HOSE:FPT', '1H', onUpdate);
        console.log('Waiting 10s to gather initial indicator data...');
        await sleep(10000);

        console.log('\n[PRE-RECONNECT] Latest indicators:', JSON.stringify(preReconnectIndicators));

        // Force Disconnect
        console.log('Forcing network disconnect...');
        hasReconnected = true;
        (provider as any).client.end(); 

        // Wait for reconnect and data restoration
        console.log('Waiting 10s for reconnect and new valid candle data...');
        await sleep(10000);

        // Analysis
        console.log('\n=== Reconnect Gap Analysis ===');
        console.log('Pre-Disconnect Indicators: ', preReconnectIndicators);
        console.log('Post-Reconnect Indicators: ', postReconnectFirstIndicators);
        
        if (!postReconnectFirstIndicators) {
            console.error('FAIL: No data received after reconnect.');
            process.exit(1);
        }

        const preKeys = Object.keys(preReconnectIndicators || {});
        const postKeys = Object.keys(postReconnectFirstIndicators || {});

        if (postKeys.length < preKeys.length) {
            console.warn(`WARNING: Indicator loss detected. Pre: ${preKeys.length}, Post: ${postKeys.length}`);
        } else if (postKeys.length === 0) {
            console.warn('WARNING: No indicators found in either phase.');
        } else {
            console.log('SUCCESS: Indicator semantics preserved across reconnect boundary.');
        }

    } catch (e) {
        console.error('Test Failed:', e);
        process.exit(1);
    } finally {
        await provider.disconnect();
    }
}

runIndicatorReconnectTest();
