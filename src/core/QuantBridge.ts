import pino from 'pino';
import { CanonicalCandle } from './interfaces';

const logger = pino({
    transport: {
        target: 'pino-pretty',
        options: { colorize: true }
    }
});

export interface QuantBridgeOptions {
    pythonEngineUrl: string; // e.g. 'http://127.0.0.1:8000'
    timeoutMs?: number;
}

/**
 * V2.0-028 & V2.0-029: Quant Bridge (Node.js Gateway -> Python Engine Transport)
 */
export class QuantBridge {
    private engineUrl: string;
    private timeoutMs: number;

    constructor(options: QuantBridgeOptions) {
        this.engineUrl = options.pythonEngineUrl.replace(/\/$/, '');
        this.timeoutMs = options.timeoutMs ?? 3000;
    }

    /**
     * Check if Python Quant Engine is reachable
     */
    public async checkHealth(): Promise<boolean> {
        try {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), this.timeoutMs);
            const res = await fetch(`${this.engineUrl}/health`, { signal: controller.signal });
            clearTimeout(timer);
            return res.ok;
        } catch (e: any) {
            logger.warn(`Python Quant Engine not reachable at ${this.engineUrl}: ${e.message}`);
            return false;
        }
    }

    /**
     * Forward incoming Canonical Candle (with TV indicator snapshot) to Python Quant Engine
     */
    public async forwardCandle(candle: CanonicalCandle): Promise<any> {
        try {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), this.timeoutMs);

            const res = await fetch(`${this.engineUrl}/events/candle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(candle),
                signal: controller.signal
            });
            clearTimeout(timer);

            if (!res.ok) {
                logger.error(`Python Engine returned error status: ${res.status}`);
                return null;
            }

            const data = await res.json();
            return data;
        } catch (e: any) {
            logger.error(`Failed to forward candle to Python Quant Engine: ${e.message}`);
            return null;
        }
    }
}
