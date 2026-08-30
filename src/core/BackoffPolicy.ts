export interface BackoffOptions {
    baseDelayMs?: number;
    maxDelayMs?: number;
    factor?: number;
    jitterFactor?: number;
    rng?: () => number;
}

export class BackoffPolicy {
    private baseDelayMs: number;
    private maxDelayMs: number;
    private factor: number;
    private jitterFactor: number;
    private rng: () => number;

    constructor(options?: BackoffOptions) {
        this.baseDelayMs = options?.baseDelayMs ?? 1000;
        this.maxDelayMs = options?.maxDelayMs ?? 60000; // Cap at 60s
        this.factor = options?.factor ?? 2;
        this.jitterFactor = options?.jitterFactor ?? 0.2; // 20% jitter
        this.rng = options?.rng ?? Math.random;
    }

    /**
     * Calculates the next delay based on the current attempt count.
     * @param attempt The current zero-indexed attempt (0 = first failure)
     */
    public calculateDelay(attempt: number): number {
        const exponentialDelay = this.baseDelayMs * Math.pow(this.factor, attempt);
        const cappedDelay = Math.min(exponentialDelay, this.maxDelayMs);
        
        // Apply Jitter: random value between (delay - jitter) and (delay + jitter)
        const jitterVariance = cappedDelay * this.jitterFactor;
        const jitter = (this.rng() * jitterVariance * 2) - jitterVariance;
        
        const finalDelay = Math.min(this.maxDelayMs, Math.max(0, cappedDelay + jitter));
        return Math.floor(finalDelay);
    }
}
