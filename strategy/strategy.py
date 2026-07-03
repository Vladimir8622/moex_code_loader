import pandas as pd
import numpy as np
from pathlib import Path
from skfolio.model_selection import WalkForward



#param
# ma_slow = 10
# ma_fast = 3
# delta = 0.5 

#data
file_path = Path('continous/GD_5min.csv')
df = pd.read_csv(file_path)


def strategy(df, ma_fast, ma_slow, delta):
    df = df.copy()
        #ma
    df['ma_fast'] = df['close'].rolling(window=ma_fast).mean()
    df['ma_slow'] = df['close'].rolling(window=ma_slow).mean()
    df['ma_diff'] = df['ma_fast'] - df['ma_slow']


    def get_position(diff):
        if diff > delta:
            return 1    
        elif diff < -delta:
            return -1  
        else:
            return 0    

    df['position'] = df['ma_diff'].apply(get_position)

    df['my_log_return'] = df['position'].shift(1) * df['log_ret']
    df['return'] = df['my_log_return'].cumsum().apply(np.exp)


    return (df['return'].iloc[-1] - 1) * 100



def optimize(train_df):

    best_profit = -np.inf
    best_params = None

    for ma_fast in range(2, 11):

        for ma_slow in range(10, 50, 5):

            if ma_fast >= ma_slow:
                continue

            for delta in np.arange(1, 50, 5):

                profit = strategy(
                    train_df,
                    ma_fast,
                    ma_slow,
                    delta,
                )

                if profit > best_profit:

                    best_profit = profit
                    best_params = (
                        ma_fast,
                        ma_slow,
                        delta,
                    )

    return best_params, best_profit

cv = WalkForward(
    train_size=20000,
    test_size=10000,
)

results = []

for fold, (train_idx, test_idx) in enumerate(cv.split(df), start=1):

    train = df.iloc[train_idx]
    test = df.iloc[test_idx]

    best_params, train_profit = optimize(train)

    test_profit = strategy(
        test,
        *best_params,
    )

    results.append({
        "fold": fold,
        "ma_fast": best_params[0],
        "ma_slow": best_params[1],
        "delta": best_params[2],
        "train_profit": train_profit,
        "test_profit": test_profit,
    })

    print(
        f"Fold {fold:2d} | "
        f"fast={best_params[0]:2d} "
        f"slow={best_params[1]:2d} "
        f"delta={best_params[2]:.2f} | "
        f"train={train_profit:.3f} | "
        f"test={test_profit:.3f}"
    )