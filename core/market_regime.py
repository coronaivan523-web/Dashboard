import pandas_ta as ta
import pandas as pd
import logging

logger = logging.getLogger("TITAN-OMNI.REGIME")

class MarketRegime:
    """
    Detector de R\u00e9gimen de Mercado v6.0.
    Clasifica el estado actual: BULL, BEAR, SIDEWAYS, VOLATILE.
    """
    @staticmethod
    def analyze(df):
        """
        Analiza un DataFrame de OHLCV y determina el r\u00e9gimen.
        """
        try:
            # Asumimos que DF ya tiene indicadores o los calculamos
            if 'EMA_200' not in df.columns:
                df.ta.ema(length=200, append=True)
            if 'RSI_14' not in df.columns:
                df.ta.rsi(length=14, append=True)
            if 'ATRr_14' not in df.columns:
                df.ta.atr(length=14, append=True)
                
            last = df.iloc[-1]
            price = last['close']
            ema200 = last['EMA_200']
            rsi = last['RSI_14']
            atr = last['ATRr_14']
            
            regime = "SIDEWAYS"
            
            # L\u00f3gica b\u00e1sica v6.0
            if price > ema200:
                if rsi > 50:
                    regime = "BULL_TREND"
                else:
                    regime = "BULL_WEAK"
            else:
                if rsi < 50:
                    regime = "BEAR_TREND"
                else:
                    regime = "BEAR_WEAK"
                    
            # Check de Volatilidad
            volatility_pct = (atr / price) * 100
            if volatility_pct > 2.0: # > 2% ATR es vol\u00e1til para 15m
                regime += "_VOLATILE"
                
            return regime, volatility_pct
            
        except Exception as e:
            logger.error(f"REGIME ERROR: {e}")
            return "UNKNOWN", 0.0
