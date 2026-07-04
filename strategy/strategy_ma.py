import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

from WOF_strategy import (
    walk_forward,
    sharpe_ratio,
    total_return,
    max_drawdown,
)


def strategy(df, ma_fast, ma_slow, delta):

    df = df.copy()

    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()
    df["ma_diff"] = df["ma_fast"] - df["ma_slow"]

    def get_position(diff):
        if diff > delta:
            return 1
        elif diff < -delta:
            return -1
        else:
            return 0

    df["position"] = df["ma_diff"].apply(get_position)

    returns = (
        df["position"].shift(1) * df["log_ret"]
    ).fillna(0)

    return returns


file_path = Path("continous/GD_5min.csv")
df = pd.read_csv(file_path)
df["begin"] = pd.to_datetime(df["begin"])

param_grid = {
    "ma_fast": range(5, 45, 5),
    "ma_slow": range(50, 500, 10),
    "delta": range(10, 510, 50),
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

oos_returns = pd.concat(wf_test_returns["sharpe"]).sort_index()
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
