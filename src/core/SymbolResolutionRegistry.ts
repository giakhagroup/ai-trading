export enum SymbolState {
    UNKNOWN = 'UNKNOWN',
    RESOLVING = 'RESOLVING',
    ACTIVE = 'ACTIVE',
    INVALID = 'INVALID',
    QUARANTINED = 'QUARANTINED'
}

export interface RegistryOptions {
    quarantineTTLMs?: number;
}

export class SymbolResolutionRegistry {
    private states: Map<string, SymbolState> = new Map();
    private quarantineTimers: Map<string, NodeJS.Timeout> = new Map();
    private quarantineTTLMs: number;

    constructor(options?: RegistryOptions) {
        this.quarantineTTLMs = options?.quarantineTTLMs ?? 300000; // default 5 mins
    }

    public markState(symbol: string, state: SymbolState): void {
        this.states.set(symbol, state);
        
        // Handle quarantine timers
        if (state === SymbolState.QUARANTINED) {
            this.setQuarantineTimer(symbol);
        } else {
            this.clearQuarantineTimer(symbol);
        }
    }

    public getState(symbol: string): SymbolState {
        return this.states.get(symbol) || SymbolState.UNKNOWN;
    }

    public isQuarantined(symbol: string): boolean {
        return this.getState(symbol) === SymbolState.QUARANTINED;
    }

    private setQuarantineTimer(symbol: string) {
        this.clearQuarantineTimer(symbol);
        const timer = setTimeout(() => {
            // Revert back to UNKNOWN so it can be retried eventually
            this.states.set(symbol, SymbolState.UNKNOWN);
            this.quarantineTimers.delete(symbol);
        }, this.quarantineTTLMs);
        
        // Don't block Node.js from exiting
        timer.unref(); 
        this.quarantineTimers.set(symbol, timer);
    }

    private clearQuarantineTimer(symbol: string) {
        const timer = this.quarantineTimers.get(symbol);
        if (timer) {
            clearTimeout(timer);
            this.quarantineTimers.delete(symbol);
        }
    }

    public getQuarantinedCount(): number {
        let count = 0;
        for (const state of this.states.values()) {
            if (state === SymbolState.QUARANTINED) count++;
        }
        return count;
    }
}
