import pandas as pd
import numpy as np
from pathlib import Path

from WOF_strategy import (
    walk_forward,
    sharpe_ratio,
    optimize,
)


def strategy(df, ma_fast, ma_slow, delta):

    df = df.copy()

    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()

    diff = df["ma_fast"] - df["ma_slow"]

    df["position"] = np.where(
        diff > delta,
        1,
        np.where(diff < -delta, -1, 0)
    )

    returns = (
        df["position"].shift(1) * df["log_ret"]
    ).fillna(0)

    return returns



file_path = Path("continous/GD_5min.csv")
df = pd.read_csv(file_path)



param_grid = {
    "ma_fast": range(2, 11),
    "ma_slow": range(10, 50, 5),
    "delta": range(1, 50, 5),
}



results = walk_forward(
    df=df,
    strategy=strategy,
    param_grid=param_grid,
    train_size=20_000,
    test_size=10_000,

    # что оптимизируем
    objective=sharpe_ratio,
)



print("\n========== RESULTS ==========\n")
print(results)

print("\nСредний Sharpe:")
print(results["test_sharpe"].mean())

print("\nСредняя доходность:")
print(results["test_return"].mean())

print("\nСредняя максимальная просадка:")
print(results["test_max_drawdown"].mean())

print("\nСовокупная доходность WFO:")

wfo_return = (results["test_return"] + 1).prod() - 1
print(f"{wfo_return:.2%}")