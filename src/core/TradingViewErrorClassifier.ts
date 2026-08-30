export enum ErrorCategory {
    INVALID_SYMBOL = 'INVALID_SYMBOL',
    TRANSIENT = 'TRANSIENT',
    CONNECTION = 'CONNECTION',
    UNKNOWN = 'UNKNOWN'
}

export class TradingViewErrorClassifier {
    /**
     * Parses the error arguments emitted by TradingView's chart.onError event
     * and categorizes them.
     */
    public classifyChartError(args: any[]): ErrorCategory {
        const errorString = args.map(a => (typeof a === 'string' ? a : JSON.stringify(a))).join(' ').toLowerCase();

        // Specific combination indicating a dead symbol
        if (errorString.includes('invalid symbol') || errorString.includes('unknown symbol')) {
            return ErrorCategory.INVALID_SYMBOL;
        }

        // Generic resolve errors
        if (errorString.includes('resolve error')) {
            // "resolve error" is usually coupled with "invalid symbol" in TradingView errors.
            // If it happens without "invalid symbol", it might be a temporary TV backend issue.
            // But per constraints, we don't quarantine *solely* on generic "resolve error", so we treat as TRANSIENT or UNKNOWN.
            return ErrorCategory.TRANSIENT;
        }

        if (errorString.includes('disconnected') || errorString.includes('timeout') || errorString.includes('network')) {
            return ErrorCategory.CONNECTION;
        }

        return ErrorCategory.UNKNOWN;
    }
}
