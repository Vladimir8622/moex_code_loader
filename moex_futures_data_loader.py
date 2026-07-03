# TODO: tickers with more than two symbols

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import datetime
import os
import requests
import apimoex
import time
from pathlib import Path
from tqdm import tqdm
import random
from requests.exceptions import ConnectionError, Timeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import utilities


data_folder = 'MOEX'

def create_robust_session():
    """
    Create a session with robust retry configuration
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Configure session with reasonable defaults
    session.headers.update({
        'User-Agent': 'MOEX Data Loader/1.0',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    })
    
    return session

def make_rets(ticker, start, end, max_retries=7, base_delay=5):
    """
    Fetch market data with enhanced retry logic and circuit breaker pattern
    """
    for attempt in range(max_retries):
        try:
            with create_robust_session() as session:
                data = apimoex.get_market_candles(
                    session=session,
                    security=ticker,
                    market="forts",
                    engine="futures",
                    interval=1,
                    start=start,
                    end=end
                )
            
            df = pd.DataFrame(data)
            if df.shape[0] > 0:
                # print(df.head())
                df.set_index("begin", inplace=True)
                df.index = pd.to_datetime(df.index)
                df.name = ticker
                df['log_ret'] = np.log(df.close).diff()
                
                # Use pathlib for robust path construction
                output_path = Path(data_folder) / f"{ticker}.csv"
                df.to_csv(output_path)
                return True
            else:
                # print(f"No data for {ticker}")
                return True
                
        except (ConnectionError, Timeout, RequestException) as e:
            if attempt < max_retries - 1:
                # Enhanced exponential backoff with longer delays
                delay = base_delay * (2 ** attempt) + random.uniform(1, 3)
                print(f"Connection error for {ticker}, attempt {attempt + 1}/{max_retries}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"Failed to fetch data for {ticker} after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            print(f"Unexpected error for {ticker}: {e}")
            return False
    
    # Longer delay between successful requests to be more respectful to the API
    time.sleep(random.uniform(5, 10))
    return False


if __name__ == '__main__':
    tickers = utilities.get_futures_active_tickers()

    month_names = np.array(['F','G','H','J','K','M','N','Q','U','V','X','Z'])
    #month_names = np.array(['V','X','Z'])

    years = np.arange(2024,2026)

    # Add progress bar for ticker processing with error tracking
    successful_requests = 0
    failed_requests = 0

    for ticker in tqdm(tickers, desc="Processing tickers", unit="ticker"):
        # print(f"\nProcessing ticker: {ticker}")
        # Use pathlib for robust path construction and create all subdirectories
        out_folder = Path(data_folder)
        out_folder.mkdir(parents=True, exist_ok=True)
        
        for year in years:
            for month in month_names:
                start = datetime.datetime(year-1, 1, 1)
                end = datetime.datetime(year+1, 1, 1)
                contract_name = ticker+month+str(year)[-1]
                
                # Check if file already exists to avoid re-downloading
                output_file = out_folder / f"{contract_name}.csv"
                if output_file.exists():
                    # print(f"  Skipping {contract_name} - file already exists")
                    continue
                    
                # print(f"  Fetching {contract_name} ({start.date()} to {end.date()})")
                success = make_rets(contract_name, start, end)
                
                if success:
                    successful_requests += 1
                else:
                    failed_requests += 1

    # print(f"\nSummary: {successful_requests} successful, {failed_requests} failed requests")


