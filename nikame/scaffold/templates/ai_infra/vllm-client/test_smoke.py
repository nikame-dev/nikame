import pytest
from app.ai_infra.vllm_client import VLLMClient

def test_client_init():
    client = VLLMClient(base_url="http://test:8000/v1", api_key="test-key")
    assert client.client.base_url == "http://test:8000/v1/"
