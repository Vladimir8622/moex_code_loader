"""
Tests for the continuous-contract construction algorithm in
moex_futures_merge.py (function `merge_futures`).

Strategy: instead of hitting the real MOEX API, we build small synthetic
per-contract CSV files with hand-chosen volume profiles (front-month volume
fading out while the next contract's volume ramps up) and check that the
algorithm:

  1. only rolls from contract A to contract B once B has become
     meaningfully more liquid than A,
  2. produces one contiguous, chronologically monotonic continuous series
     stitched strictly from A before the roll date and from B after it,
  3. writes exactly one row per rollover to <ticker>_rolls.csv,
  4. does nothing (no output files) for tickers with no data at all,
  5. does not roll at all when there is only a single contract.

These are "characterisation + correctness" tests: they don't assume any
particular rollover date, they assert the *properties* the continuous
series must satisfy for it to be usable as a trading series.
"""
import sys
import os
import shutil
import tempfile
import unittest
import datetime as dt

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stubs'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import moexalgo  # stub, needed by moex_futures_merge's own get_futures_active_tickers
import moex_futures_merge as mfm


def _write_contract_csv(folder, contract_name, start_date, n_days, volumes,
                         price=100.0):
    """Write one synthetic '1-minute' candle file (1 row/day is enough,
    since the algorithm only cares about the daily-resampled volume)."""
    dates = [start_date + dt.timedelta(days=i) for i in range(n_days)]
    df = pd.DataFrame({
        'begin': [d.strftime('%Y-%m-%d %H:%M:%S') for d in dates],
        'open': price,
        'high': price * 1.01,
        'low': price * 0.99,
        'close': price,
        'value': [v * price for v in volumes],
        'volume': volumes,
        'log_ret': 0.0,
    })
    df.to_csv(folder / f'{contract_name}.csv', index=False)


class MergeFuturesRolloverTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data_folder = None  # set per test
        # month_names/years used by generate_names() inside moex_futures_merge
        self.month_names = np.array(
            ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _paths(self):
        from pathlib import Path
        data_folder = Path(self.tmp) / 'MOEX'
        out_folder = Path(self.tmp) / 'continous'
        summary_folder = Path(self.tmp) / 'summary'
        for p in (data_folder, out_folder, summary_folder):
            p.mkdir(parents=True, exist_ok=True)
        return data_folder, out_folder, summary_folder

    def test_rolls_from_fading_front_to_rising_back_contract(self):
        data_folder, out_folder, summary_folder = self._paths()
        ticker = 'RI'
        start = dt.datetime(2025, 1, 1)
        n_days = 40

        # Front contract: highly liquid for the first 20 days, then fades.
        vol_front = [1000] * 20 + [max(1000 - (i - 19) * 100, 10) for i in range(20, n_days)]
        # Back contract: quiet for 20 days, then ramps up hard.
        vol_back = [50] * 20 + [50 + (i - 19) * 150 for i in range(20, n_days)]

        _write_contract_csv(data_folder, f'{ticker}H5', start, n_days, vol_front)
        _write_contract_csv(data_folder, f'{ticker}M5', start, n_days, vol_back)

        moexalgo.Market.tickers = lambda self: [{'ticker': f'{ticker}H5'}]

        mfm.merge_futures(data_folder, out_folder, summary_folder)

        rolls_path = summary_folder / f'{ticker}_rolls.csv'
        continuous_path = out_folder / f'{ticker}_1min.csv'
        self.assertTrue(rolls_path.exists(), "rolls csv should be created")
        self.assertTrue(continuous_path.exists(), "continuous series should be created")

        rolls = pd.read_csv(rolls_path)
        self.assertEqual(len(rolls), 1, "exactly one rollover expected between 2 contracts")
        self.assertEqual(rolls.iloc[0]['ticker1'], f'{ticker}H5')
        self.assertEqual(rolls.iloc[0]['ticker2'], f'{ticker}M5')

        roll_date = pd.to_datetime(rolls.iloc[0]['date'])
        # Roll must happen only once the back contract is actually the
        # more liquid one, i.e. strictly after day 20 (index 19).
        self.assertGreaterEqual(roll_date, start + dt.timedelta(days=20))

        continuous = pd.read_csv(continuous_path, index_col=0)
        continuous.index = pd.to_datetime(continuous.index)

        # Chronological, non-decreasing index (usable as a price series).
        self.assertTrue((continuous.index.to_series().diff().dropna() >= dt.timedelta(0)).all())

        before = continuous[continuous.index < roll_date]
        after = continuous[continuous.index >= roll_date]
        self.assertTrue((before['ticker'] == f'{ticker}H5').all(),
                         "everything before the roll date must come from the front contract")
        self.assertTrue((after['ticker'] == f'{ticker}M5').all(),
                         "everything from the roll date onward must come from the back contract")
        self.assertGreater(len(before), 0)
        self.assertGreater(len(after), 0)

    def test_no_data_produces_no_output(self):
        data_folder, out_folder, summary_folder = self._paths()
        moexalgo.Market.tickers = lambda self: [{'ticker': 'ZZH5'}]

        mfm.merge_futures(data_folder, out_folder, summary_folder)

        self.assertFalse((summary_folder / 'ZZ_rolls.csv').exists())
        self.assertFalse((out_folder / 'ZZ_1min.csv').exists())

    def test_single_contract_never_rolls(self):
        data_folder, out_folder, summary_folder = self._paths()
        ticker = 'SI'
        start = dt.datetime(2025, 1, 1)
        n_days = 15
        volumes = [500] * n_days
        _write_contract_csv(data_folder, f'{ticker}H5', start, n_days, volumes)

        moexalgo.Market.tickers = lambda self: [{'ticker': f'{ticker}H5'}]

        mfm.merge_futures(data_folder, out_folder, summary_folder)

        rolls = pd.read_csv(summary_folder / f'{ticker}_rolls.csv')
        self.assertEqual(len(rolls), 0, "a single contract must never generate a rollover")

        continuous = pd.read_csv(out_folder / f'{ticker}_1min.csv', index_col=0)
        self.assertTrue((continuous['ticker'] == f'{ticker}H5').all())


if __name__ == '__main__':
    unittest.main()
