"""
Tests for utilities.py

These tests use a stub `moexalgo` module (see stubs/moexalgo.py) so no
network access is required. The stub's Market.tickers() is monkeypatched
per-test to return controlled fixture data.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stubs'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import moexalgo  # stub
import utilities


class TestGetFuturesActiveTickers(unittest.TestCase):

    def test_strips_last_two_symbols_and_dedupes(self):
        raw = [
            {'ticker': 'RIH5'},   # -> RI
            {'ticker': 'RIM5'},   # -> RI (duplicate root)
            {'ticker': 'SiH5'},   # -> Si
            {'ticker': 'BRZ5'},   # -> BR
        ]
        moexalgo.Market.tickers = lambda self: raw

        result = utilities.get_futures_active_tickers()

        # Root ticker = full code minus the last 2 characters (month+year digit)
        self.assertEqual(result, ['RI', 'Si', 'BR'])

    def test_empty_market_raises_keyerror_bug(self):
        """
        Regression test documenting a real bug found by this test suite:
        get_futures_active_tickers() does `pd.DataFrame(tickers)['ticker']`.
        When the exchange returns an empty ticker list, pd.DataFrame([])
        has no 'ticker' column at all, so this raises KeyError instead of
        returning an empty list. A transient empty/failed API response
        would crash the whole pipeline instead of degrading gracefully.
        Suggested fix: guard with `if not tickers: return []` before
        building the DataFrame.
        """
        moexalgo.Market.tickers = lambda self: []
        with self.assertRaises(KeyError):
            utilities.get_futures_active_tickers()

    def test_three_letter_root_is_mishandled(self):
        """
        Regression test documenting a known limitation (see TODO in
        moex_futures_data_loader.py: 'tickers with more than two symbols').
        Root-ticker extraction is hard-coded as ticker[:-2], which silently
        assumes every contract code is root + 1 month letter + 1 year digit.
        For MOEX this is usually true, but the code has no validation and
        will silently produce a wrong (truncated) root for any ticker whose
        naming convention differs. This test locks in current behaviour so
        a future fix is a conscious, visible change rather than an
        accidental regression.
        """
        moexalgo.Market.tickers = lambda self: [{'ticker': 'ABCDEFZ5'}]
        result = utilities.get_futures_active_tickers()
        # Currently just chops the last two characters, right or wrong.
        self.assertEqual(result, ['ABCDEF'])


class TestGenerateNames(unittest.TestCase):

    def test_generate_names_shape(self):
        moexalgo.Market.tickers = lambda self: [{'ticker': 'RIH5'}]
        month_names, years, tickers = utilities.generate_names()

        self.assertEqual(list(month_names),
                          ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'])
        self.assertEqual(list(years), [2022, 2023, 2024, 2025])
        self.assertEqual(tickers, ['RI'])


if __name__ == '__main__':
    unittest.main()
