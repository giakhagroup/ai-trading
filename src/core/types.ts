export enum Timeframe {
    M1 = '1',
    M5 = '5',
    M15 = '15',
    M30 = '30',
    H1 = '60',
    H4 = '240',
    D1 = '1D',
    W1 = '1W',
    MN1 = '1M'
}

export enum SessionType {
    ATO = 'ATO',
    CONTINUOUS = 'CONTINUOUS',
    LUNCH = 'LUNCH',
    ATC = 'ATC',
    NEGOTIATED = 'NEGOTIATED'
}

export enum AssetClass {
    STOCK = 'STOCK',
    CRYPTO = 'CRYPTO',
    FOREX = 'FOREX',
    COMMODITY = 'COMMODITY',
    INDEX = 'INDEX'
}

export enum QualityStatus {
    REALTIME = 'REALTIME',
    DELAYED = 'DELAYED',
    HISTORICAL = 'HISTORICAL',
    UNVERIFIED = 'UNVERIFIED',
    CORRUPTED = 'CORRUPTED'
}
