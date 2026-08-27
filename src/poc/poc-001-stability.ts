import TradingView from '@mathieuc/tradingview';
import pino from 'pino';

// Cấu hình logger để dễ dàng quan sát
const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true
    }
  }
});

logger.info('Starting POC-001: 24-Hour Stability Test...');

// Khởi tạo client WebSocket
const client = new TradingView.Client(); 

client.onError((err: any) => {
    logger.error({ err }, 'TradingView Client Error');
});

// Khởi tạo Chart Session cho FPT (M5)
const chartFpt = new client.Session.Chart();
chartFpt.setMarket('HOSE:FPT', {
  timeframe: '5',
});

chartFpt.onError((...err: any[]) => {
  logger.error({ err }, 'Chart FPT Error');
});

chartFpt.onSymbolLoaded(() => {
  logger.info(`Market FPT loaded! Timeframe: 5M`);
});

chartFpt.onUpdate(() => {
  if (!chartFpt.periods[0]) return;
  const candle = chartFpt.periods[0];
  logger.info(`[FPT] Close: ${candle.close} | Vol: ${candle.volume} | Time: ${new Date(candle.time * 1000).toISOString()}`);
});

// Khởi tạo Chart Session cho XAUUSD (M1)
const chartGold = new client.Session.Chart();
chartGold.setMarket('OANDA:XAUUSD', {
  timeframe: '1',
});

chartGold.onError((...err: any[]) => {
  logger.error({ err }, 'Chart XAUUSD Error');
});

chartGold.onSymbolLoaded(() => {
  logger.info(`Market XAUUSD loaded! Timeframe: 1M`);
});

chartGold.onUpdate(() => {
  if (!chartGold.periods[0]) return;
  const candle = chartGold.periods[0];
  logger.info(`[XAUUSD] Close: ${candle.close} | Vol: ${candle.volume} | Time: ${new Date(candle.time * 1000).toISOString()}`);
});

// Script này sẽ được để chạy ngầm liên tục 24h trên môi trường local
// (Có thể dùng pm2 hoặc nodemon để theo dõi)
