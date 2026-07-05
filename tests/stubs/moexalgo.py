"""Lightweight stub of moexalgo used only for tests (no network access)."""

class Market:
    def __init__(self, name):
        self.name = name

    def tickers(self):
        # Overridable in tests via monkeypatch of Market.tickers
        return []
