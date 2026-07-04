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
import yaml

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

def make_rets(ticker, start, end, data_folder, max_retries=7, base_delay=5):
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
                df.set_index("begin", inplace=True)
                df.index = pd.to_datetime(df.index)
                df.name = ticker
                # Возможны Nan в этом столбце
                df['log_ret'] = np.log(df.close).diff()
                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                output_path = data_folder / f"{ticker}.csv"
                df.to_csv(output_path)
                # delay between successful requests to be more respectful to the API
                time.sleep(random.uniform(2,3))
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
    
    return False

if __name__ == '__main__':
    # Подгрузка конфигурации запуска
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    # Проверка необходимости запускать скрипт
    if config['load']['enabled']:
        # Use pathlib for robust path construction
        data_folder = Path(config['general']['data_folder'])

        tickers = utilities.get_futures_active_tickers()

        month_names = config['general']['months']

        years = config['general']['years']

        # Add progress bar for ticker processing with error tracking
        successful_requests = 0
        failed_requests = 0

        for ticker in tqdm(tickers, desc="Processing tickers", unit="ticker"):

            out_folder = data_folder
            out_folder.mkdir(parents=True, exist_ok=True)
            
            for year in years:
                for month in month_names:
                    start = datetime.datetime(year, 1, 1)
                    end = datetime.datetime(year+1, 1, 1)
                    contract_name = ticker+month+str(year)[-1]
                    
                    # Check if file already exists to avoid re-downloading
                    output_file = out_folder / f"{contract_name}.csv"
                    if output_file.exists():
                        continue
                        
                    success = make_rets(contract_name, start, end, data_folder)
                    
                    if success:
                        successful_requests += 1
                    else:
                        failed_requests += 1
