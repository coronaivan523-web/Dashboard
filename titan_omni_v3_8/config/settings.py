import os

# SYSTEM
SYSTEM_MODE = os.getenv("SYSTEM_MODE", "PAPER").upper()
CYCLE_ID_OVERRIDE = os.getenv("CYCLE_ID_OVERRIDE")

# TRADING
SYMBOL = os.getenv("SYMBOL", "BTC/USD")
TIMEFRAME = os.getenv("TIMEFRAME", "15m")
START_CAPITAL = float(os.getenv("START_CAPITAL", "10000.0"))

# SECRETS (Names only, values must come from env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_SECRET = os.getenv("KRAKEN_SECRET")
