
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stubs'))
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


if __name__ == '__main__':
    unittest.main()
