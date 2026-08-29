import { SessionType, Timeframe, AssetClass, QualityStatus } from './types';

/**
 * V2.0-006: Provider Capability Contract
 */
export interface ProviderCapabilities {
    realtime: boolean;
    historical: boolean;
    quotes: boolean;
    ohlcv: boolean;
    multiSymbol: boolean;
    multiTimeframe: boolean;
    builtInIndicators: boolean;
    pineIndicators: boolean;
    replay: boolean;
    screener: boolean;
}

/**
 * V2.0-005: Provider Abstraction
 */
export interface MarketDataProvider {
    name: string;
    capabilities: ProviderCapabilities;
    
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    
    // Thêm các hàm nghiệp vụ khi cần thiết (subscribe, getHistorical, ...)
}

/**
 * V2.0-012: Canonical Market Data Contract
 */
export interface CanonicalCandle {
    event_id: string;
    provider: string;
    provider_symbol: string;
    internal_symbol: string;
    exchange: string;
    asset_class: string;
    currency: string;
    timezone: string;
    timeframe: string;
    
    source_timestamp: number;
    event_timestamp: number;
    received_at: number;
    processed_at: number;
    
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    
    is_closed: boolean;
    sequence: number;
    revision: number;
    quality_status: string;
    quality_score: number;
    
    // V2.0-015: Market Session Data Semantics
    session_type?: SessionType;
    is_auction?: boolean;
}
