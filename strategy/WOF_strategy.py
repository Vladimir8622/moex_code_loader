from itertools import product
import numpy as np
import pandas as pd
from skfolio.model_selection import WalkForward



def total_return(returns: pd.Series) -> float:
    returns = returns.fillna(0)
    return np.exp(returns.sum()) - 1


def max_drawdown(returns: pd.Series) -> float:
    returns = returns.fillna(0)

    equity = np.exp(returns.cumsum())
    peak = equity.cummax()
    drawdown = equity / peak - 1

    return drawdown.min()


def sharpe_ratio(returns: pd.Series) -> float:
    returns = returns.fillna(0)
    std = returns.std()
    if std == 0:
        return -np.inf
    return returns.mean() / std



def optimize(
    train_df,
    strategy,
    param_grid,
    objective=sharpe_ratio,
):
 

    best_score = -np.inf
    best_params = None

    names = list(param_grid.keys())

    for values in product(*param_grid.values()):

        params = dict(zip(names, values))

        returns = strategy(train_df.copy(), **params)

        score = objective(returns)

        if score > best_score:
            best_score = score
            best_params = params

    return best_params, best_score



def walk_forward(
    df,
    strategy,
    param_grid,
    train_size,
    test_size,
    objective=sharpe_ratio,
):


    cv = WalkForward(
        train_size=train_size,
        test_size=test_size,
    )

    results = []

    for fold, (train_idx, test_idx) in enumerate(cv.split(df), start=1):

        train = df.iloc[train_idx]
        test = df.iloc[test_idx]

        best_params, train_score = optimize(
            train,
            strategy,
            param_grid,
            objective,
        )

        test_returns = strategy(
            test.copy(),
            **best_params,
        )

        results.append({
            "fold": fold,
            **best_params,

            "train_score": train_score,

            "test_return": total_return(test_returns),
            "test_sharpe": sharpe_ratio(test_returns),
            "test_max_drawdown": max_drawdown(test_returns),
        })

        print(
            f"Fold {fold:2d} | "
            f"params={best_params} | "
            f"score={train_score:.4f}"
        )

    return pd.DataFrame(results)