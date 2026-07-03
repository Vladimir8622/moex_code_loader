"""
load_summary.py runs its logic at *import time* (no `if __name__ == '__main__'`
guard), reads a hard-coded relative 'MOEX' folder and calls the live MOEX API
via utilities.generate_names(). That makes it unsafe to unit-test via a
normal `import` (see code review notes). Instead we run it as a subprocess
in a temp working directory, with the stub modules on PYTHONPATH, against a
small fixture data set, and check the pipeline completes and produces the
expected plots.

This also indirectly documents a real bug: month-letter extraction assumes
every ticker root is exactly 2 characters (`file[2:3]`), which contradicts
the TODO in moex_futures_data_loader.py ("tickers with more than two
symbols"). tickers whose root is not 2 characters would be silently
mis-classified as "quarterly" (empty intersection with monthly month
letters) instead of raising an error.
"""
import os
import sys
import shutil
import tempfile
import subprocess
import unittest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
STUBS = os.path.join(PROJECT_ROOT, 'stubs')


class LoadSummarySmokeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.moex_dir = os.path.join(self.tmp, 'MOEX')
        os.makedirs(self.moex_dir)
        # one monthly-style ticker (2-char root 'RI', month letter present
        # in only_monthly_month_names) and one quarterly-style ('SI')
        open(os.path.join(self.moex_dir, 'RIF5.csv'), 'w').write('begin\n2025-01-01\n')
        open(os.path.join(self.moex_dir, 'SIH5.csv'), 'w').write('begin\n2025-03-01\n')
        for f in ('load_summary.py', 'utilities.py'):
            shutil.copy(os.path.join(PROJECT_ROOT, f), self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pipeline_crashes_on_missing_contract_files_bug(self):
        """
        This documents a real, serious bug found by running the script
        end-to-end: summary_plot() computes
            markersize = 0.5 * np.log(row['file_size'])
        for EVERY (ticker, year, month) combination, including the many
        combinations where no CSV file exists (file_size == 0, the normal
        case -- most tickers don't trade every one of the 12 month
        letters). log(0) = -inf, which matplotlib can't use as a marker
        size, and the script crashes instead of skipping missing points.
        In real usage this reliably crashes load_summary.py, so
        update_data.py's pipeline stops after step 1 and never reaches
        step 3 (merge). Suggested fix: filter out rows with
        file_size == 0 before plotting, e.g.
        `df_ticker[df_ticker['file_size'] > 0]`.
        """
        # a tiny fixture-aware moexalgo stub returning our two roots
        fixture_moexalgo = (
            "class Market:\n"
            "    def __init__(self, name):\n"
            "        pass\n"
            "    def tickers(self):\n"
            "        return [{'ticker': 'RIF5'}, {'ticker': 'SIH5'}]\n"
        )
        fixture_dir = os.path.join(self.tmp, 'fixture_stubs')
        os.makedirs(fixture_dir)
        with open(os.path.join(fixture_dir, 'moexalgo.py'), 'w') as fh:
            fh.write(fixture_moexalgo)
        shutil.copy(os.path.join(STUBS, 'tqdm.py'), fixture_dir)
        shutil.copy(os.path.join(STUBS, 'apimoex.py'), fixture_dir)

        env = dict(os.environ)
        env['PYTHONPATH'] = fixture_dir + os.pathsep + env.get('PYTHONPATH', '')
        env['MPLBACKEND'] = 'Agg'

        result = subprocess.run(
            [sys.executable, 'load_summary.py'],
            cwd=self.tmp, env=env, capture_output=True, text=True, timeout=60,
        )

        self.assertNotEqual(result.returncode, 0,
                             "expected the known log(0) marker-size bug to crash the script; "
                             "if this now passes, the bug has been fixed and this test (and the "
                             "one below) should be updated to assert success instead")
        self.assertIn('SystemError', result.stderr + result.stdout,
                       "expected the matplotlib/PIL crash caused by markersize=-inf")


    def test_pipeline_succeeds_once_zero_size_rows_are_filtered(self):
        """
        Sanity check for the suggested fix: patching summary_plot to drop
        file_size == 0 rows before plotting (the minimal one-line fix)
        lets the whole pipeline complete and produce both plots.
        """
        patched = os.path.join(self.tmp, 'load_summary.py')
        with open(patched) as fh:
            src = fh.read()
        fixed_src = src.replace(
            "for _, row in df_ticker.iterrows():",
            "for _, row in df_ticker[df_ticker['file_size'] > 0].iterrows():",
        )
        self.assertNotEqual(src, fixed_src, "patch target line not found - script must have changed")
        with open(patched, 'w') as fh:
            fh.write(fixed_src)

        # Use >=3 tickers per bucket: summary_plot() also has a second,
        # independent bug where figsize=(len(series)/4, len(tickers)/3)
        # is computed with *integer* division, so e.g. 1-2 tickers yields
        # a figure height of 0 and crashes matplotlib/PIL regardless of
        # the log(0) fix. Using 3 tickers per bucket isolates the fix
        # under test to just the log(0) issue (that separate figsize bug
        # is documented on its own below).
        for name in ('RIF5', 'RJF5', 'RKF5'):
            open(os.path.join(self.moex_dir, f'{name}.csv'), 'w').close()
        for name in ('SIH5', 'SJH5', 'SKH5'):
            open(os.path.join(self.moex_dir, f'{name}.csv'), 'w').close()

        fixture_moexalgo = (
            "class Market:\n"
            "    def __init__(self, name):\n"
            "        pass\n"
            "    def tickers(self):\n"
            "        return [{'ticker': t} for t in "
            "['RIF5', 'RJF5', 'RKF5', 'SIH5', 'SJH5', 'SKH5']]\n"
        )
        fixture_dir = os.path.join(self.tmp, 'fixture_stubs')
        os.makedirs(fixture_dir)
        with open(os.path.join(fixture_dir, 'moexalgo.py'), 'w') as fh:
            fh.write(fixture_moexalgo)
        shutil.copy(os.path.join(STUBS, 'tqdm.py'), fixture_dir)
        shutil.copy(os.path.join(STUBS, 'apimoex.py'), fixture_dir)

        env = dict(os.environ)
        env['PYTHONPATH'] = fixture_dir + os.pathsep + env.get('PYTHONPATH', '')
        env['MPLBACKEND'] = 'Agg'

        result = subprocess.run(
            [sys.executable, 'load_summary.py'],
            cwd=self.tmp, env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0,
                          f"still crashing after the fix:\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}")
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp, 'summary', 'summary_check_monthly.png')))
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp, 'summary', 'summary_check_quarterly.png')))

    def test_figsize_zero_bug_with_few_tickers(self):
        """
        Documents a second, independent bug in summary_plot(): figsize is
        computed as (int(len(series_names)/4), int(len(tickers)/3)) using
        *integer* division. With few tickers in a bucket (very plausible -
        not every root trades every month letter) this rounds down to 0,
        producing an invalid (zero height/width) matplotlib figure and
        crashing on savefig(), independently of the log(0) bug above.
        Suggested fix: use max(1, ...) around each dimension, e.g.
        figsize=(max(1, len(series_names)//4), max(1, len(tickers)//3)).
        """
        # Single quarterly ticker -> int(1/3) == 0 -> figsize height 0.
        open(os.path.join(self.moex_dir, 'SIH5.csv'), 'w').close()

        fixture_moexalgo = (
            "class Market:\n"
            "    def __init__(self, name):\n"
            "        pass\n"
            "    def tickers(self):\n"
            "        return [{'ticker': 'SIH5'}]\n"
        )
        fixture_dir = os.path.join(self.tmp, 'fixture_stubs')
        os.makedirs(fixture_dir)
        with open(os.path.join(fixture_dir, 'moexalgo.py'), 'w') as fh:
            fh.write(fixture_moexalgo)
        shutil.copy(os.path.join(STUBS, 'tqdm.py'), fixture_dir)
        shutil.copy(os.path.join(STUBS, 'apimoex.py'), fixture_dir)

        env = dict(os.environ)
        env['PYTHONPATH'] = fixture_dir + os.pathsep + env.get('PYTHONPATH', '')
        env['MPLBACKEND'] = 'Agg'

        result = subprocess.run(
            [sys.executable, 'load_summary.py'],
            cwd=self.tmp, env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertNotEqual(result.returncode, 0,
                             "expected a crash from the zero-height figsize bug; "
                             "if this now passes, the bug has been fixed and this "
                             "test should be updated to assert success instead")


if __name__ == '__main__':
    unittest.main()
