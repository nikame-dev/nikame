import pytest
from app.ai_infra.tgi_client import TGIClient

def test_client_init():
    client = TGIClient(base_url="http://tgi-server:8080")
    assert client.client.base_url == "http://tgi-server:8080"
