from itertools import product
import numpy as np
import pandas as pd
from numba import njit
from skfolio.model_selection import WalkForward



@njit(cache=True)
def rolling_mean_nb(x, window):
    n = x.shape[0]
    out = np.full(n, np.nan)
    csum = 0.0
    for i in range(n):
        csum += x[i]
        if i >= window:
            csum -= x[i - window]
        if i >= window - 1:
            out[i] = csum / window
    return out


@njit(cache=True)
def total_return_nb(returns):
    s = 0.0
    for i in range(returns.shape[0]):
        v = returns[i]
        if not np.isnan(v):
            s += v
    return np.exp(s) - 1.0


@njit(cache=True)
def max_drawdown_nb(returns):
    n = returns.shape[0]
    cum = 0.0
    peak = 1.0
    max_dd = 0.0
    for i in range(n):
        v = returns[i]
        if np.isnan(v):
            v = 0.0
        cum += v
        equity = np.exp(cum)
        if equity > peak:
            peak = equity
        dd = equity / peak - 1.0
        if dd < max_dd:
            max_dd = dd
    return max_dd


@njit(cache=True)
def sharpe_ratio_nb(returns):
    n = returns.shape[0]
    s = 0.0
    for i in range(n):
        v = returns[i]
        if np.isnan(v):
            v = 0.0
        s += v
    mean = s / n

    var = 0.0
    for i in range(n):
        v = returns[i]
        if np.isnan(v):
            v = 0.0
        var += (v - mean) ** 2

    if n > 1:
        var /= (n - 1)  
    else:
        var = 0.0

    std = np.sqrt(var)
    if std == 0.0:
        return -np.inf
    return mean / std



def _as_array(returns):
    if isinstance(returns, pd.Series):
        return returns.to_numpy(dtype=np.float64)
    return np.asarray(returns, dtype=np.float64)


def total_return(returns):
    return total_return_nb(_as_array(returns))


def max_drawdown(returns):
    return max_drawdown_nb(_as_array(returns))


def sharpe_ratio(returns):
    return sharpe_ratio_nb(_as_array(returns))




def optimize(train_close, train_log_ret, strategy, param_grid, objectives):
    # для каждой метрики свой лучший результат
    best_params = {name: None for name in objectives}
    best_score = {name: -np.inf for name in objectives}

    names = list(param_grid.keys())

    for values in product(*param_grid.values()):
        params = dict(zip(names, values))

        returns = strategy(train_close, train_log_ret, **params)

        for name, objective in objectives.items():
            score = objective(returns)
            if score > best_score[name]:
                best_score[name] = score
                best_params[name] = params

    return best_params, best_score


def walk_forward(df, strategy, param_grid, train_size, test_size, objectives):

    cv = WalkForward(train_size=train_size, test_size=test_size)

    close_all = df["close"].to_numpy(dtype=np.float64)
    log_ret_all = df["log_ret"].to_numpy(dtype=np.float64)

    results = {name: [] for name in objectives}

    test_returns_all = {name: [] for name in objectives}

    for fold, (train_idx, test_idx) in enumerate(cv.split(df), start=1):

        train_close = close_all[train_idx]
        train_log_ret = log_ret_all[train_idx]

        test_close = close_all[test_idx]
        test_log_ret = log_ret_all[test_idx]

        best_params, best_score = optimize(
            train_close, train_log_ret, strategy, param_grid, objectives
        )

        for name in objectives:
            params = best_params[name]

            test_returns = strategy(test_close, test_log_ret, **params)
            test_returns_all[name].append((test_idx, test_returns))

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