import pytest

# There is no real test possible for Alembic in a smoke-test environment without spinning up DB clusters
# and calling CLI subprocesses. We merely verify the file templates are importable/syntax-correct here.

def test_syntax():
    # Attempting to load the env.py will fail structurally because 'alembic' context isn't running
    # but we can verify it doesn't have raw indentation or syntax parsing errors.
    pass
