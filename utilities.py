from moexalgo import Market
import pandas as pd
import numpy as np


def get_futures_active_tickers():
    eq = Market('futures')
    tickers = eq.tickers()
    tickers = pd.DataFrame(tickers)['ticker'].tolist()

    # Remove last 2 symbols from each ticker
    tickers = [ticker[:-2] for ticker in tickers]
    tickers = pd.Series(tickers).unique().tolist()

    return(tickers)

def generate_names():
    month_names = np.array(['F','G','H','J','K','M','N','Q','U','V','X','Z'])
    years = np.arange(2022,2026)
    tickers = get_futures_active_tickers()
    return(month_names, years, tickers)

