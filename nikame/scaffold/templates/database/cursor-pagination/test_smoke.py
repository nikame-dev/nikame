import pytest
from app.database.cursor_pagination import encode_cursor, decode_cursor, CursorParams, get_cursor_params

def test_cursor_encoding_decoding():
    val = 1459
    encoded = encode_cursor(val)
    
    # Ensure it doesn't look like a raw integer string
    assert str(val) != encoded
    
    decoded = decode_cursor(encoded, type_func=int)
    assert decoded == val

def test_cursor_params_defaults():
    params = get_cursor_params(cursor=None, limit=20)
    assert params.limit == 20
    assert params.cursor is None

def test_cursor_decode_invalid_returns_none():
    assert decode_cursor("invalid-base64!!", int) is None
