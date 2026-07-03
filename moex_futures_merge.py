import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib
matplotlib.use('Agg')
import datetime
from pathlib import Path
import utilities
import tqdm
from moexalgo import Market



def merge_futures(data_folder, out_folder, summary_folder):
    month_names, years, tickers = generate_names()
    for ticker in tqdm.tqdm(tickers, desc='Merging futures', unit='ticker'):
        # print(ticker)
        candles = pd.DataFrame()
        volumes_prev = pd.DataFrame()
        rolls = pd.DataFrame({'ticker1': [], 'ticker2': [], 'date': []})
        
        plt.figure(figsize = (16, 12), dpi = 300)

        prev_rollover_date = datetime.datetime(1900, 1, 1)

        data_exists = False
        
        for year in years:
            for month in month_names:
                contract_name = ticker+month+str(year)[-1]
                if os.path.isfile(data_folder / f'{contract_name}.csv'):

                    if not data_exists:
                        data_exists = True

                    temp_candles = pd.read_csv(data_folder / f'{contract_name}.csv', index_col = 'begin')
                    temp_candles.index = pd.to_datetime(temp_candles.index, format = '%Y-%m-%d %H:%M:%S')
                    temp_candles['ticker'] = contract_name
                    volumes = pd.DataFrame(temp_candles['volume'].resample('1d').sum())
                    volumes.columns = [contract_name]
                    
                    plt.fill_between(volumes.index,np.log(1+volumes).values.flatten())

                    # np.log(1+volumes).plot(kind='area')

                    if volumes_prev.shape[0]!=0:
                        volumes_meged = volumes_prev.merge(volumes, how = 'outer', left_index = True, right_index = True)
                        volumes_meged = volumes_meged.fillna(0)
                        
                        next_more_liquid_dates = volumes_meged.index[(volumes_meged.iloc[:,0]<volumes_meged.iloc[:,1]) &
                        (volumes_meged.iloc[:,1]>0.2*np.quantile(volumes_meged.iloc[:,1], 0.95, axis=0)) &
                        (volumes_meged.sum(axis=1)>0.05*np.quantile(volumes_meged.sum(axis=1), 0.95, axis=0))]

                        next_more_liquid_dates = next_more_liquid_dates[next_more_liquid_dates>prev_rollover_date]
                        
                        if len(next_more_liquid_dates)>0:

                            rollover_date = next_more_liquid_dates[0]
                            
                            if (volumes_prev.index[-1]>rollover_date):
                                rollover_date = rollover_date + datetime.timedelta(days=1)
                                
                            
                            rolls.loc[len(rolls.index)] = [volumes_meged.columns[0], volumes_meged.columns[1], rollover_date]
                            # print(volumes_meged.columns[0], rollover_date)
        
                            candles_before = candles[candles.index < rollover_date]
                            candles_after = temp_candles[temp_candles.index >= rollover_date]
                            candles = pd.concat([candles_before, candles_after], ignore_index=False)
                            plt.axvline(x=rollover_date, color = 'red')
                            volumes_prev = volumes
                            prev_rollover_date = rollover_date
                    else:
                        rollover_date = volumes.index[(volumes.iloc[:,0]>0.5*np.quantile(volumes.iloc[:,0], 0.9, axis=0))][0]
                        candles = temp_candles[rollover_date:]
                        volumes_prev = volumes

        if data_exists:
            rolls.to_csv(summary_folder / f'{ticker}_rolls.csv')
            plt.title(ticker)
            plt.savefig(summary_folder / f'{ticker}_rolls.png', dpi = 300)
            candles.to_csv(out_folder / f'{ticker}_1min.csv')

        plt.close('all')
            

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

def merge_5min(out_folder):
    month_names, years, tickers = generate_names()
    for ticker in tqdm.tqdm(tickers, desc='Merging 5min', unit='ticker'):
        # print(ticker)
        onemin_file = out_folder / f'{ticker}_1min.csv'
        if os.path.isfile(onemin_file):
            candles_1min = pd.read_csv(onemin_file, index_col = 'begin')
            candles_1min.index = pd.to_datetime(candles_1min.index, format = '%Y-%m-%d %H:%M:%S')

            candles_5min = candles_1min.resample('5min').agg({'open': 'first', 
                                                                'close': 'last', 
                                                                'high': 'max', 
                                                                'low': 'min',
                                                                'value':'sum',
                                                                'volume':'sum',
                                                                'log_ret':'sum',
                                                                'ticker':'first'})
            candles_5min = candles_5min.dropna()
            candles_5min.to_csv(out_folder / f'{ticker}_5min.csv')

if __name__ == '__main__':

    data_folder = Path('MOEX')
    summary_folder = Path('summary')
    summary_folder.mkdir(parents=True, exist_ok=True)
    out_folder = Path('continous')
    out_folder.mkdir(parents=True, exist_ok=True)

    merge_futures(data_folder, out_folder, summary_folder)
    merge_5min(out_folder)