import TradingView from '@mathieuc/tradingview';
import pino from 'pino';

const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: { colorize: true }
  }
});

logger.info('Starting POC-009: Rate Limit & Disconnect Simulation');

// Hàm tạo một client và lập tức đóng để spam TradingView WSS
async function spamConnections(count: number, delayMs: number) {
  for (let i = 0; i < count; i++) {
    try {
      logger.info(`Attempt ${i + 1}/${count} - Creating Client`);
      const client = new TradingView.Client();
      
      client.onError((err: any) => {
        logger.error({ err }, `Client ${i + 1} Error`);
      });

      // Mở session
      const chart = new client.Session.Chart();
      chart.setMarket('BINANCE:BTCUSDT', { timeframe: '1' });
      
      chart.onSymbolLoaded(() => {
        logger.info(`Client ${i + 1} Connected successfully.`);
        // Sau khi connect thành công thì ngắt kết nối luôn để thử thách rate limit
        client.end();
      });

      // Tạo delay ngắn để không bị chặn IP ở mức network layer ngay lập tức, 
      // mà tập trung test application layer (HTTP 429 / WSS ban)
      await new Promise(resolve => setTimeout(resolve, delayMs));
    } catch (e) {
      logger.error({ e }, `Exception at attempt ${i + 1}`);
    }
  }
}

// Chạy 50 kết nối liên tục cách nhau 500ms
spamConnections(50, 500).then(() => {
  logger.info('POC-009 script execution finished. Please check logs for 429 errors or connection rejections.');
});
