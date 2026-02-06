import ccxt
import pandas as pd
import pandas_ta as ta
from config import settings

class MarketDataProvider:
    def __init__(self):
        if not settings.KRAKEN_API_KEY or not settings.KRAKEN_SECRET:
            # Not strictly raising here to allow initialization, but usage will fail or logic handles it to fail-closed if critical
            pass
        
        self.exchange = ccxt.kraken({
            'apiKey': settings.KRAKEN_API_KEY,
            'secret': settings.KRAKEN_SECRET,
            'enableRateLimit': True
        })

    def get_data(self, symbol, timeframe):
        try:
            # 1. Ticker for Spread
            ticker = self.exchange.fetch_ticker(symbol)
            bid = ticker['bid']
            ask = ticker['ask']
            last = ticker['last']
            
            # Spread Guard
            if not bid or bid <= 0 or not ask or ask <= 0:
                spread_pct = 1.0 # Force SKIP
            else:
                spread_pct = (ask - bid) / ask

            # 2. OHLCV for Indicators
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # 3. Indicators
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=200, append=True)
            df.ta.atr(length=14, append=True)
            
            latest = df.iloc[-1]
            
            return {
                "price": last,
                "rsi": latest['RSI_14'],
                "ema_200": latest['EMA_200'],
                "atr": latest['ATRr_14'],
                "spread_pct": spread_pct,
                "df": df # Keep full df if auditor needs context (optional)
            }
        except Exception as e:
            # Fail-closed implies we assume worst case or re-raise
            # Returning None allows caller to handle "Data Unavailable"
            return None
