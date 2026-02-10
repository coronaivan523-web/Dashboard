import ccxt
import pandas as pd
import logging

logger = logging.getLogger("TITAN-OMNI.SCANNER")

class Scanner:
    """
    Esc\u00e1ner de Oportunidades v6.0.
    Reduce el universo de activos al TOP 1 candidato para Hunting.
    """
    def __init__(self, exchange):
        self.exchange = exchange
        self.whitelist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"] # Universo reducido para demo

    def scan_top_asset(self):
        """
        Escanea la whitelist y devuelve el mejor candidato basado en volumen y tendencia.
        Retorna: (symbol, score, metadata)
        """
        logger.info("SCANNER: Iniciando barrido de mercado...")
        best_asset = None
        best_score = -1
        
        try:
            tickers = self.exchange.fetch_tickers(self.whitelist)
            
            for symbol, ticker in tickers.items():
                if not ticker: continue
                
                # Criterio simple v6.0: Volumen en Quote (USDT) * Cambio 24h absoluto
                vol_usd = ticker['quoteVolume'] if ticker.get('quoteVolume') else 0
                change_pct = abs(ticker['percentage']) if ticker.get('percentage') else 0
                
                score = vol_usd * (1 + change_pct)
                
                if score > best_score:
                    best_score = score
                    best_asset = symbol
            
            logger.info(f"SCANNER: Activo ganador identificado -> {best_asset} (Score: {best_score:.2f})")
            return best_asset
            
        except Exception as e:
            logger.error(f"SCANNER ERROR: {e}")
            return "BTC/USDT" # Fallback seguro

    # UNIV-SCANNER-01: Multi-Asset Listing (Ordered)
    def scan_assets(self):
        """
        Escanea la whitelist y devuelve LISTA ORDENADA de candidatos
        basado en volumen y tendencia (Score desc).
        Retorna: [symbol1, symbol2, ...]
        """
        logger.info("SCANNER: Iniciando barrido MULTI-ACTIVO...")
        scored_assets = []
        
        try:
            tickers = self.exchange.fetch_tickers(self.whitelist)
            
            for symbol, ticker in tickers.items():
                if not ticker: continue
                
                vol_usd = ticker['quoteVolume'] if ticker.get('quoteVolume') else 0
                change_pct = abs(ticker['percentage']) if ticker.get('percentage') else 0
                score = vol_usd * (1 + change_pct)
                
                scored_assets.append((symbol, score))
            
            # Ordenar por Score Descendente
            scored_assets.sort(key=lambda x: x[1], reverse=True)
            
            result_list = [x[0] for x in scored_assets]
            logger.info(f"SCANNER: Lista ordenada identificada -> {result_list}")
            return result_list
            
        except Exception as e:
            logger.error(f"SCANNER ERROR: {e}")
            return ["BTC/USDT"] # Fallback seguro lista
