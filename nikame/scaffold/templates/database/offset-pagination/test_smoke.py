import pytest
from app.database.offset_pagination import get_pagination_params, PaginationParams

def test_pagination_params_parser():
    params = get_pagination_params(page=2, size=50)
    assert params.page == 2
    assert params.size == 50

def test_pagination_params_defaults():
    params = get_pagination_params()
    assert params.page == 1
    assert params.size == 20
