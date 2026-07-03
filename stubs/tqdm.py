"""Minimal stub of tqdm (progress bar) with the same call signature used in
the project, so real project code can run in a headless test environment."""

def tqdm(iterable=None, *args, **kwargs):
    if iterable is None:
        return _DummyBar()
    return iterable

class _DummyBar:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def update(self, *a, **k): pass
    def close(self): pass
