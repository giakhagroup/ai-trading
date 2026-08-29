import { CanonicalCandle, MarketDataProvider } from './interfaces';

type SubscriptionCallback = (candle: CanonicalCandle) => void;

/**
 * V2.0-011: Shared Subscription Aggregator
 */
export class SubscriptionAggregator {
    private provider: MarketDataProvider;
    // Map: symbol_timeframe -> list of callbacks
    private subscribers: Map<string, Set<SubscriptionCallback>> = new Map();

    constructor(provider: MarketDataProvider) {
        this.provider = provider;
    }

    public getSubscriptionKey(symbol: string, timeframe: string): string {
        return `${symbol}_${timeframe}`;
    }

    public async subscribe(symbol: string, timeframe: string, callback: SubscriptionCallback): Promise<void> {
        const key = this.getSubscriptionKey(symbol, timeframe);
        
        if (!this.subscribers.has(key)) {
            this.subscribers.set(key, new Set());
            // TODO: Actually call provider.subscribe(...) here since it's the first listener
        }
        
        this.subscribers.get(key)!.add(callback);
    }

    public async unsubscribe(symbol: string, timeframe: string, callback: SubscriptionCallback): Promise<void> {
        const key = this.getSubscriptionKey(symbol, timeframe);
        const callbacks = this.subscribers.get(key);
        
        if (callbacks) {
            callbacks.delete(callback);
            
            if (callbacks.size === 0) {
                this.subscribers.delete(key);
                // TODO: Actually call provider.unsubscribe(...) here since no one is listening anymore
            }
        }
    }

    /**
     * Provider will call this method when new data arrives
     */
    public onDataReceived(symbol: string, timeframe: string, candle: CanonicalCandle): void {
        const key = this.getSubscriptionKey(symbol, timeframe);
        const callbacks = this.subscribers.get(key);
        
        if (callbacks) {
            for (const callback of callbacks) {
                try {
                    callback(candle);
                } catch (err) {
                    console.error('Error in subscriber callback:', err);
                }
            }
        }
    }
}
