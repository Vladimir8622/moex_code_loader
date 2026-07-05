
import sys
import os
import shutil
import tempfile
import unittest
import datetime as dt

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stubs'))
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


def _make_config(months, years):
    return {'general': {'months': months, 'years': years}}


class MergeFuturesRolloverTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # full month-letter set is used across tests; each test's config
        # only needs to include the letters actually present in its
        # fixture files, but using the full set keeps this generic.
        self.all_months = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']

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
        config = _make_config(self.all_months, [2025])

        mfm.merge_futures(data_folder, out_folder, summary_folder, config)

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
        config = _make_config(self.all_months, [2025])

        mfm.merge_futures(data_folder, out_folder, summary_folder, config)

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
        config = _make_config(self.all_months, [2025])

        mfm.merge_futures(data_folder, out_folder, summary_folder, config)

        rolls = pd.read_csv(summary_folder / f'{ticker}_rolls.csv')
        self.assertEqual(len(rolls), 0, "a single contract must never generate a rollover")

        continuous = pd.read_csv(out_folder / f'{ticker}_1min.csv', index_col=0)
        self.assertTrue((continuous['ticker'] == f'{ticker}H5').all())

    def test_config_year_not_matching_data_produces_no_output(self):
        """
        merge_futures() only looks for files named '<ticker><month><last
        digit of year>.csv' for the (month, year) combinations present in
        config['general']. If the config's `years` doesn't match the
        actual data on disk, the ticker is silently treated as having no
        data at all - this is worth locking in explicitly since it's an
        easy misconfiguration (e.g. forgetting to update config.yaml's
        `years` list for a new year) that fails silently rather than
        raising an error.
        """
        data_folder, out_folder, summary_folder = self._paths()
        ticker = 'RI'
        start = dt.datetime(2024, 1, 1)  # data is for 2024...
        _write_contract_csv(data_folder, f'{ticker}H4', start, 10, [500] * 10)

        moexalgo.Market.tickers = lambda self: [{'ticker': f'{ticker}H4'}]
        config = _make_config(self.all_months, [2025])  # ...but config only asks for 2025

        mfm.merge_futures(data_folder, out_folder, summary_folder, config)

        self.assertFalse((summary_folder / f'{ticker}_rolls.csv').exists())
        self.assertFalse((out_folder / f'{ticker}_1min.csv').exists())


class Merge5MinTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_resamples_1min_to_5min_ohlcv(self):
        from pathlib import Path
        out_folder = Path(self.tmp)

        # 10 minutes of synthetic 1-minute candles -> should produce 2
        # complete 5-minute bars.
        times = pd.date_range('2025-01-01 10:00:00', periods=10, freq='1min')
        df = pd.DataFrame({
            'begin': times.strftime('%Y-%m-%d %H:%M:%S'),
            'open': range(1, 11),
            'high': [v + 1 for v in range(1, 11)],
            'low': [v - 1 for v in range(1, 11)],
            'close': range(1, 11),
            'value': [100] * 10,
            'volume': [10] * 10,
            'log_ret': [0.01] * 10,
            'ticker': 'RIH5',
        })
        df.to_csv(out_folder / 'RI_1min.csv', index=False)

        moexalgo.Market.tickers = lambda self: [{'ticker': 'RIH5'}]

        mfm.merge_5min(out_folder)

        out_file = out_folder / 'RI_5min.csv'
        self.assertTrue(out_file.exists())

        result = pd.read_csv(out_file, index_col=0)
        self.assertEqual(len(result), 2)
        # first 5-min bar: open of first row, close of 5th row
        self.assertEqual(result.iloc[0]['open'], 1)
        self.assertEqual(result.iloc[0]['close'], 5)
        self.assertEqual(result.iloc[0]['volume'], 50)  # 5 rows * 10
        self.assertEqual(result.iloc[0]['ticker'], 'RIH5')

    def test_missing_1min_file_produces_no_5min_output(self):
        from pathlib import Path
        out_folder = Path(self.tmp)
        moexalgo.Market.tickers = lambda self: [{'ticker': 'ZZH5'}]

        mfm.merge_5min(out_folder)

        self.assertFalse((out_folder / 'ZZ_5min.csv').exists())

import yaml

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

if __name__ == '__main__' and config['test']['enabled'] :
    unittest.main()
