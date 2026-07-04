from itertools import product
import numpy as np
import pandas as pd
from skfolio.model_selection import WalkForward


def total_return(returns):
    returns = returns.fillna(0)
    return np.exp(returns.sum()) - 1


def max_drawdown(returns):
    returns = returns.fillna(0)
    equity = np.exp(returns.cumsum())
    peak = equity.cummax()
    drawdown = equity / peak - 1
    return drawdown.min()


def sharpe_ratio(returns):
    returns = returns.fillna(0)
    std = returns.std()
    if std == 0:
        return -np.inf
    return returns.mean() / std


def optimize(train_df, strategy, param_grid, objectives):
    # для каждой метрики свой лучший результат
    best_params = {name: None for name in objectives}
    best_score = {name: -np.inf for name in objectives}

    names = list(param_grid.keys())

    for values in product(*param_grid.values()):
        params = dict(zip(names, values))

        returns = strategy(train_df.copy(), **params)

        for name, objective in objectives.items():
            score = objective(returns)
            if score > best_score[name]:
                best_score[name] = score
                best_params[name] = params

    return best_params, best_score


def walk_forward(df, strategy, param_grid, train_size, test_size, objectives):

    cv = WalkForward(train_size=train_size, test_size=test_size)

    results = {name: [] for name in objectives}
    test_returns_all = {name: [] for name in objectives}

    for fold, (train_idx, test_idx) in enumerate(cv.split(df), start=1):

        train = df.iloc[train_idx]
        test = df.iloc[test_idx]

        best_params, best_score = optimize(train, strategy, param_grid, objectives)

        for name in objectives:
            params = best_params[name]

            test_returns = strategy(test.copy(), **params)
            test_returns_all[name].append(test_returns)

            results[name].append({
                "fold": fold,
                **params,
                "train_score": best_score[name],
                "test_return": total_return(test_returns),
                "test_sharpe": sharpe_ratio(test_returns),
                "test_max_drawdown": max_drawdown(test_returns),
            })

        print(f"Fold {fold} done, params: {best_params}")

    results = {name: pd.DataFrame(rows) for name, rows in results.items()}
    return results, test_returns_all