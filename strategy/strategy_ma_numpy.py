import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import time  
import os
from numba import njit
from WOF_numpy import rolling_mean_nb

os.makedirs("strategy/graphs_and_stats/data",exist_ok=True)

from WOF_numpy import (
    walk_forward,
    sharpe_ratio,
    total_return,
    max_drawdown,
)

start_time = time.time()



@njit(cache=True)
def strategy(close, log_ret,
             ma_fast,
             ma_slow,
             tp,
             sl):

    ma_fast_arr = rolling_mean_nb(close, ma_fast)
    ma_slow_arr = rolling_mean_nb(close, ma_slow)

    n = close.shape[0]

    returns = np.zeros(n)

    # 0 - нет позиции
    # 1 - long
    # -1 - short
    position = 0

    entry_price = 0.0
    tp_price = 0.0
    sl_price = 0.0

    for i in range(1, n):

        # считаем доходность текущей свечи
        returns[i] = position * log_ret[i]

        # пока MA не появились
        if np.isnan(ma_fast_arr[i]) or np.isnan(ma_slow_arr[i]):
            continue

        # ==========================
        # Проверяем TP/SL
        # ==========================

        if position == 1:

            if close[i] >= tp_price or close[i] <= sl_price:
                position = 0

        elif position == -1:

            if close[i] <= tp_price or close[i] >= sl_price:
                position = 0



        if position != 0:
            continue

        prev_diff = ma_fast_arr[i-1] - ma_slow_arr[i-1]
        curr_diff = ma_fast_arr[i]   - ma_slow_arr[i]


        if prev_diff <= 0.0 and curr_diff > 0.0:

            position = 1
            entry_price = close[i]

            tp_price = entry_price * (1.0 + tp)
            sl_price = entry_price * (1.0 - sl)

        

    return returns




file_path = Path("continous/GD_5min.csv")
df = pd.read_csv(file_path)
df["begin"] = pd.to_datetime(df["begin"])

param_grid = {
    "ma_fast": range(5, 45, 5),
    "ma_slow": range(50, 500, 50),
    "tp": np.arange(0.01, 0.1, 0.001),
    "sl": np.arange(0.01, 0.1, 0.001),
}

objectives = {
    "sharpe": sharpe_ratio,
    "total_return": total_return,
    "max_drawdown": max_drawdown,
}

wf_results, wf_test_returns = walk_forward(
    df=df,
    strategy=strategy,
    param_grid=param_grid,
    train_size=10_000,
    test_size=5_000,
    objectives=objectives,
)

results_sharpe = wf_results["sharpe"]
results_total = wf_results["total_return"]
results_max = wf_results["max_drawdown"]

results_sharpe.to_csv("strategy/graphs_and_stats/results_sharpe.csv", index=False)
results_total.to_csv("strategy/graphs_and_stats/results_total_return.csv", index=False)
results_max.to_csv("strategy/graphs_and_stats/results_max_drawdown.csv", index=False)

ma_fast_period = 50
ma_slow_period = 200
df['ma_fast1'] = df['close'].rolling(window=ma_fast_period).mean()
df['ma_slow1'] = df['close'].rolling(window=ma_slow_period).mean()

plt.figure(figsize=(14, 7))
plt.plot(df['begin'], df['close'],
         color='black', linewidth=1.5, label='Close Price')
plt.plot(df['begin'], df['ma_fast1'],
         color='blue', linewidth=2, label=f'MA Fast ({ma_fast_period})')
plt.plot(df['begin'], df['ma_slow1'],
         color='red', linewidth=2, label=f'MA Slow ({ma_slow_period})')
plt.xlabel('Дата', fontsize=12)
plt.ylabel('Цена', fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("strategy/graphs_and_stats/price_ma.png", dpi=300, bbox_inches="tight")
plt.show()

plt.figure(figsize=(10, 6))
plt.hist(df["log_ret"].dropna(), bins=100)
plt.xlabel("Log Return")
plt.ylabel("Frequency")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("strategy/graphs_and_stats/log_ret.png", dpi=300, bbox_inches="tight")
plt.show()

series_list = [
    pd.Series(ret, index=idx)
    for idx, ret in wf_test_returns["sharpe"]
]

oos_returns = pd.concat(series_list).sort_index()
equity = np.exp(oos_returns.cumsum())
dates = df.loc[oos_returns.index, "begin"]

plt.figure(figsize=(14, 7))
plt.plot(dates, equity, color='green', linewidth=1.5)
plt.title("Equity (walk-forward, out-of-sample)")
plt.xlabel('Data')
plt.ylabel('Equity')
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("strategy/graphs_and_stats/equity.png", dpi=300, bbox_inches="tight")
plt.show()

plt.figure(figsize=(10, 5))
plt.bar(results_sharpe["fold"], results_sharpe["test_return"])
plt.xlabel("Fold")
plt.ylabel("Total Return")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("strategy/graphs_and_stats/total_return.png", dpi=300, bbox_inches="tight")

plt.show()

plt.figure(figsize=(10, 5))
plt.bar(results_sharpe["fold"], results_sharpe["test_sharpe"])
plt.title("Sharpe Ratio by Walk Forward Window")
plt.xlabel("Fold")
plt.ylabel("Sharpe Ratio")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("strategy/graphs_and_stats/sharpe.png", dpi=300, bbox_inches="tight")

plt.show()

plt.figure(figsize=(10, 5))
plt.bar(results_sharpe["fold"], results_sharpe["test_max_drawdown"])
plt.title("Maximum Drawdown by Walk Forward Window")
plt.xlabel("Fold")
plt.ylabel("Max Drawdown")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("strategy/graphs_and_stats/drawdown.png", dpi=300, bbox_inches="tight")
plt.show()

end_time = time.time()
execution_time = end_time - start_time

if execution_time < 60:
    print(f"\n Время выполнения скрипта: {execution_time:.2f} секунд")
elif execution_time < 3600:
    minutes = int(execution_time // 60)
    seconds = execution_time % 60
    print(f"\n Время выполнения скрипта: {minutes} мин {seconds:.2f} сек")
