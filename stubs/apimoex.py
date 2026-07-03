"""Lightweight stub of apimoex used only so the real project modules can be
imported/tested without network access. Not a functional MOEX client."""

def get_market_candles(session=None, security=None, market=None, engine=None,
                        interval=None, start=None, end=None):
    return []
