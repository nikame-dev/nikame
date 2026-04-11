import pytest
from app.ai_infra.ollama_client import OllamaClient

def test_client_init():
    client = OllamaClient(host="http://localhost:11434")
    assert client.client.host == "http://localhost:11434"
