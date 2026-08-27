import TradingView from '@mathieuc/tradingview';
import pino from 'pino';

const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: { colorize: true }
  }
});

logger.info('Starting POC-010: Study Capacity Benchmark');

// Mục đích: Kiểm tra 1 Chart Session có thể load bao nhiêu Indicator cùng lúc
async function testStudyCapacity(maxStudies: number) {
  const client = new TradingView.Client();
  
  client.onError((err: any) => {
    logger.error({ err }, 'Client Error');
  });

  const chart = new client.Session.Chart();
  chart.setMarket('BINANCE:BTCUSDT', { timeframe: '1' });
  
  chart.onSymbolLoaded(() => {
    logger.info(`Market loaded successfully. Adding ${maxStudies} studies...`);
    
    // Khởi tạo nhiều volume indicators (do volume không yêu cầu auth)
    // Trong thực tế, sẽ test với các MACD, RSI, PineScript...
    for (let i = 0; i < maxStudies; i++) {
      try {
        const volumeIndicator = new TradingView.BuiltInIndicator('Volume@tv-basicstudies-241');
        const study = new chart.Study(volumeIndicator);
        
        study.onReady(() => {
          logger.info(`Study ${i + 1}/${maxStudies} loaded.`);
        });

        study.onError((err: any) => {
          logger.error({ err }, `Study ${i + 1} Error`);
        });
      } catch (err) {
        logger.error({ err }, `Failed to add study ${i + 1}`);
      }
    }
  });
}

// Thử tải 10 indicators trên cùng 1 session
testStudyCapacity(10);
