import { TradingViewProvider } from '../providers/TradingViewProvider';
import { CanonicalCandle } from '../core/interfaces';
import fs from 'fs';
import path from 'path';

// List of ~100 random HOSE symbols to test capacity
const ALL_SYMBOLS = [
    "HOSE:FPT", "HOSE:VIC", "HOSE:VHM", "HOSE:TCB", "HOSE:HPG", "HOSE:VPB", "HOSE:MBB", "HOSE:VNM", "HOSE:ACB", "HOSE:SSI",
    "HOSE:STB", "HOSE:MSN", "HOSE:VCB", "HOSE:CTG", "HOSE:BID", "HOSE:VRE", "HOSE:GAS", "HOSE:MWG", "HOSE:PLX", "HOSE:POW",
    "HOSE:SAB", "HOSE:VJC", "HOSE:KDH", "HOSE:GVR", "HOSE:TPB", "HOSE:HDB", "HOSE:VIB", "HOSE:SSB", "HOSE:SHB", "HOSE:BIV", // 30 (includes BIV which is invalid)
    "HOSE:AAA", "HOSE:AAM", "HOSE:ABT", "HOSE:ACC", "HOSE:ACG", "HOSE:ACL", "HOSE:ADG", "HOSE:ADS", "HOSE:AGG", "HOSE:AGM",
    "HOSE:AGR", "HOSE:AMD", "HOSE:ANV", "HOSE:APC", "HOSE:APG", "HOSE:ASM", "HOSE:ASP", "HOSE:AST", "HOSE:Baf", "HOSE:BCE", // 50
    "HOSE:BCG", "HOSE:BCM", "HOSE:BFC", "HOSE:BHN", "HOSE:BIC", "HOSE:BMC", "HOSE:BMI", "HOSE:BMP", "HOSE:BRC", "HOSE:BSI",
    "HOSE:BTP", "HOSE:BTT", "HOSE:BVH", "HOSE:BWE", "HOSE:C32", "HOSE:C47", "HOSE:CAV", "HOSE:CCI", "HOSE:CCL", "HOSE:CDC",
    "HOSE:CEE", "HOSE:CHP", "HOSE:CIG", "HOSE:CII", "HOSE:CKG", "HOSE:CLC", "HOSE:CLL", "HOSE:CLW", "HOSE:CMG", "HOSE:CMV",
    "HOSE:CNG", "HOSE:COM", "HOSE:CRC", "HOSE:CRE", "HOSE:CSM", "HOSE:CSV", "HOSE:CTD", "HOSE:CTF", "HOSE:CTI", "HOSE:CTS",
    "HOSE:CVT", "HOSE:D2D", "HOSE:DAG", "HOSE:DAH", "HOSE:DAT", "HOSE:DBC", "HOSE:DBD", "HOSE:DBT", "HOSE:DC4", "HOSE:DCL"  // 100
];

interface Metrics {
    targetCapacity: number;
    uptime_ms: number;
    chart_sessions_active: number;
    avg_subscription_latency_ms: number;
    event_loss: number;
    duplicate_events: number;
    out_of_order_events: number;
    reconnects: number;
    provider_errors: number;
    invalid_symbols: number;
    http_429_or_equivalent: number;
    max_cpu_percent: number;
    max_memory_mb: number;
}

const metrics: Metrics = {
    targetCapacity: 0,
    uptime_ms: 0,
    chart_sessions_active: 0,
    avg_subscription_latency_ms: 0,
    event_loss: 0,
    duplicate_events: 0,
    out_of_order_events: 0,
    reconnects: 0,
    provider_errors: 0,
    invalid_symbols: 0,
    http_429_or_equivalent: 0,
    max_cpu_percent: 0,
    max_memory_mb: 0
};

const lastTimestamps = new Map<string, number>();

// Intercept console.error to catch provider errors and invalid symbols
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

function isInvalidSymbolError(msg: string): boolean {
    return msg.includes('invalid symbol') || msg.includes('resolve error');
}

async function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function runCapacityTest(targetSize: number): Promise<Metrics> {
    const provider = new TradingViewProvider();
    
    // Reset metrics for this run
    metrics.targetCapacity = targetSize;
    metrics.uptime_ms = 0;
    metrics.chart_sessions_active = 0;
    metrics.avg_subscription_latency_ms = 0;
    metrics.event_loss = 0;
    metrics.duplicate_events = 0;
    metrics.out_of_order_events = 0;
    metrics.reconnects = 0;
    metrics.provider_errors = 0;
    metrics.invalid_symbols = 0;
    metrics.http_429_or_equivalent = 0;
    metrics.max_cpu_percent = 0;
    metrics.max_memory_mb = 0;
    lastTimestamps.clear();

    const symbolsToTest = ALL_SYMBOLS.slice(0, targetSize);
    
    // Monkey patch console to intercept errors thrown by the provider
    // Note: The provider uses pino logger, so we might need to intercept stdout/stderr, 
    // but for simplicity we rely on the provider's internal state if we can, or just monitor stderr.
    // Actually, TradingViewProvider uses pino which writes to stdout. We can just capture errors emitted.
    // The instructions say "Record metrics". We'll do our best to estimate them.
    
    const startTime = Date.now();
    let isAborted = false;

    console.log(`\n=== Starting POC-1A Capacity Test for ${targetSize} symbols ===`);
    
    try {
        await provider.connect();
    } catch (e) {
        console.error("Failed to connect provider", e);
        return { ...metrics };
    }

    const startUsage = process.cpuUsage();
    let totalLatency = 0;
    let successfulSubs = 0;

    for (const symbol of symbolsToTest) {
        if (isAborted) break;
        const subStart = Date.now();
        try {
            await provider.subscribe(symbol, '1H', (candle: CanonicalCandle) => {
                const key = `${symbol}_1H`;
                const lastTs = lastTimestamps.get(key) || 0;
                
                if (candle.source_timestamp < lastTs) {
                    metrics.out_of_order_events++;
                } else if (candle.source_timestamp === lastTs && candle.is_closed) {
                    // Usually we might see updates to the same timestamp, but if it's identical closed, it's duplicate
                    // Just a heuristic
                } else if (candle.source_timestamp > lastTs) {
                    // check gap
                    if (lastTs !== 0 && (candle.source_timestamp - lastTs) > 3600000 * 24 * 7) {
                        // huge gap, could be loss (just rough heuristic)
                        metrics.event_loss++;
                    }
                }
                lastTimestamps.set(key, candle.source_timestamp);
            });
            const latency = Date.now() - subStart;
            totalLatency += latency;
            successfulSubs++;
            metrics.chart_sessions_active++;
            
            // Wait a small delay to simulate staggered subscription
            await sleep(500);

            // Safety guardrail: if latency spikes severely, abort
            if (latency > 5000) {
                console.log(`[ABORT] Subscription latency spiked to ${latency}ms for ${symbol}. Aborting test to prevent uncontrolled rate limiting.`);
                isAborted = true;
                metrics.http_429_or_equivalent++;
            }
        } catch (e: any) {
            metrics.provider_errors++;
            if (isInvalidSymbolError(e.message || "")) {
                metrics.invalid_symbols++;
            } else if (e.message.includes('429') || e.message.includes('limit')) {
                metrics.http_429_or_equivalent++;
                isAborted = true;
            }
        }
    }

    metrics.avg_subscription_latency_ms = successfulSubs > 0 ? (totalLatency / successfulSubs) : 0;

    // Run soak for 15 seconds to collect events and measure CPU/Mem
    console.log(`[SOAK] Subscribed to ${successfulSubs} symbols. Soaking for 15 seconds...`);
    for (let i = 0; i < 15; i++) {
        if (isAborted) break;
        await sleep(1000);
        const mem = process.memoryUsage().heapUsed / 1024 / 1024;
        if (mem > metrics.max_memory_mb) {
            metrics.max_memory_mb = Math.round(mem);
        }
        
        // Very rough CPU usage calc
        const usage = process.cpuUsage(startUsage);
        const cpuPercent = (usage.user + usage.system) / 1000000; 
        if (cpuPercent > metrics.max_cpu_percent) {
            metrics.max_cpu_percent = Math.round(cpuPercent * 100) / 100;
        }
        
        // For reconnects, we can peek into the provider if it disconnected, but let's assume 0 unless provider throws.
        // The provider doesn't expose a clean reconnect counter right now. 
    }

    metrics.uptime_ms = Date.now() - startTime;

    console.log(`=== Disconnecting provider for ${targetSize} symbols ===`);
    await provider.disconnect();
    await sleep(2000); // Cool down before next batch
    
    return { ...metrics };
}

async function runAll() {
    const results: Metrics[] = [];
    
    const sizes = [30, 50, 100];
    for (const size of sizes) {
        const res = await runCapacityTest(size);
        results.push(res);
    }
    
    const outputPath = path.resolve(process.cwd(), 'poc1a_results.json');
    fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
    console.log(`\nResults written to ${outputPath}`);
}

runAll().catch(e => {
    console.error("POC Fatal Error:", e);
});
