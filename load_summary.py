# TODO поменять на PATH логику для симметричности кода
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from pathlib import Path
import pandas as pd
import utilities
import yaml

def summary_plot(tickers, month_names, years, size_summary_folder, data_folder, plot_filename = 'summary_check.png'):
    # Обьявлено в main
    # size_summary_folder = Path('summary')
    size_summary_folder.mkdir(parents=True, exist_ok=True)
    files = os.listdir(path=data_folder)

    series_names = []
    for year in years:
        for month in month_names:
            # Take last digit of year and concatenate with month
            series_names.append(month + str(year)[-1])
    series_names = np.array(series_names)

    plt.figure(figsize=(max(3,int(len(series_names)/4)),max(3,int(len(tickers)/3))))

    file_sizes = []
    for ticker in tickers:
        for year in years:
            for month in month_names:
                file = ticker+month+str(year)[-1]+'.csv'
                file_size = 0
                if file in files:
                    file_size = os.path.getsize(data_folder / file)
                file_sizes.append({
                    'ticker': ticker,
                    'year': year,
                    'month': month,
                    'series_name': month+str(year)[-1],
                    'file_size': file_size
                })

    df_sizes = pd.DataFrame(file_sizes)

    # Sort tickers by sum of file sizes descending
    ticker_order = (
        df_sizes.groupby('ticker')['file_size']
        .sum()
        .sort_values(ascending=True)
        .index
        .tolist()
    )

    # Plot in new order
    for ticker in ticker_order:
        df_ticker = df_sizes[(df_sizes['ticker'] == ticker)]
        for _, row in df_ticker.iterrows():
            # print(row['series_name'],ticker,row['file_size'])
            size = 0.5 * np.log(row['file_size']) if row['file_size'] > 0 else 0.1
            plt.plot(
                row['series_name'],
                ticker,
                's',
                color='tab:green',
                markersize=size
            )

    plt.yticks(np.arange(len(ticker_order)),ticker_order)
    plt.xticks(np.arange(len(series_names)),series_names,rotation=90)
    plt.savefig(size_summary_folder / plot_filename)
    plt.close('all')

if __name__ == '__main__':
    # Подгрузка конфигурации запуска
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Проверка необходимости запускать скрипт
    if config['summary']['enabled']:

        data_folder = Path(config['general']['data_folder'])
        size_summary_folder = Path(config['general']['summary_of_loading_folder'])
        

        only_monthly_month_names = config['summary']['monthly_months']
        quaterly_month_names = config['summary']['quarterly_months']

        tickers_monthly = []
        tickers_quarterly = []

        month_names = config['general']['months']
        years = config['general']['years']
        tickers = utilities.get_futures_active_tickers()

        files = os.listdir(path=data_folder)

        for ticker in tickers:
            ticker_files = [file for file in files if file.startswith(ticker)]
            month_names_in_files = sorted(set([file[2:3] for file in ticker_files]))
            if len(set(only_monthly_month_names) & set(month_names_in_files))==0:
                tickers_quarterly.append(ticker)
            else:
                tickers_monthly.append(ticker)

        summary_plot(tickers_quarterly,quaterly_month_names,years,size_summary_folder,data_folder,'summary_check_quarterly.png')
        summary_plot(tickers_monthly,month_names,years,size_summary_folder,data_folder,'summary_check_monthly.png')