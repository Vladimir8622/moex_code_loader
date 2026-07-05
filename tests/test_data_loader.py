
import sys
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stubs'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from requests.exceptions import ConnectionError as ReqConnectionError

import moex_futures_data_loader as loader


class MakeRetsTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_csv_with_log_returns_on_success(self):
        fake_candles = [
            {'begin': '2025-01-01 10:00:00', 'open': 100, 'close': 101,
             'high': 102, 'low': 99, 'volume': 10, 'value': 1000},
            {'begin': '2025-01-01 10:01:00', 'open': 101, 'close': 103,
             'high': 104, 'low': 100, 'volume': 20, 'value': 2000},
        ]
        with mock.patch('apimoex.get_market_candles', return_value=fake_candles), \
             mock.patch('time.sleep', return_value=None):
            ok = loader.make_rets('RIH5', start=None, end=None, data_folder=self.tmp)

        self.assertTrue(ok)
        out_file = self.tmp / 'RIH5.csv'
        self.assertTrue(out_file.exists())

        df = pd.read_csv(out_file, index_col='begin')
        self.assertIn('log_ret', df.columns)
        # log(103/101) for the second row
        self.assertAlmostEqual(df['log_ret'].iloc[1], 0.019608, places=5)
        # first row has no prior value -> NaN
        self.assertTrue(pd.isna(df['log_ret'].iloc[0]))

    def test_empty_response_returns_true_and_writes_nothing(self):
        with mock.patch('apimoex.get_market_candles', return_value=[]):
            ok = loader.make_rets('NOSUCHTICKER', start=None, end=None, data_folder=self.tmp)
        self.assertTrue(ok)
        self.assertFalse((self.tmp / 'NOSUCHTICKER.csv').exists())

    def test_retries_then_succeeds_after_transient_connection_errors(self):
        calls = {'n': 0}

        def flaky(*args, **kwargs):
            calls['n'] += 1
            if calls['n'] < 3:
                raise ReqConnectionError('simulated network blip')
            return [{'begin': '2025-01-01 10:00:00', 'open': 1, 'close': 1,
                      'high': 1, 'low': 1, 'volume': 1, 'value': 1}]

        with mock.patch('apimoex.get_market_candles', side_effect=flaky), \
             mock.patch('time.sleep', return_value=None):  # skip real backoff delay
            ok = loader.make_rets('RIH5', start=None, end=None, data_folder=self.tmp, max_retries=5)

        self.assertTrue(ok)
        self.assertEqual(calls['n'], 3)

    def test_gives_up_after_max_retries(self):
        with mock.patch('apimoex.get_market_candles',
                         side_effect=ReqConnectionError('down')), \
             mock.patch('time.sleep', return_value=None):
            ok = loader.make_rets('RIH5', start=None, end=None, data_folder=self.tmp, max_retries=3)
        self.assertFalse(ok)
        self.assertFalse((self.tmp / 'RIH5.csv').exists())

    def test_unexpected_exception_returns_false_without_retry(self):
        calls = {'n': 0}

        def boom(*args, **kwargs):
            calls['n'] += 1
            raise ValueError('unexpected parsing error')

        with mock.patch('apimoex.get_market_candles', side_effect=boom):
            ok = loader.make_rets('RIH5', start=None, end=None, data_folder=self.tmp, max_retries=5)

        self.assertFalse(ok)
        self.assertEqual(calls['n'], 1, "non-network exceptions must not be retried")

import yaml

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

if __name__ == '__main__' and config['test']['enabled'] :
    unittest.main()
