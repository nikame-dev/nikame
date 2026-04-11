# Ollama Client

A specialized client for interacting with **Ollama**, the most popular tool for running LLMs locally.

## Why Ollama?

Ollama makes it incredibly easy to manage multiple models on your local machine or server. It handles model downloading, GGUF conversion, and GPU offloading automatically.

## Usage

```python
from app.ai_infra.ollama_client import ollama_client

@app.post("/chat")
async def chat(prompt: str):
    response = await ollama_client.chat(
        model="llama3", 
        messages=[{"role": "user", "content": prompt}]
    )
    return {"response": response['message']['content']}
```

## Vision Support

If you use a model like `llava`, you can pass image data:

```python
with open('image.jpg', 'rb') as f:
    res = await ollama_client.vision('llava', 'what is in this image?', [f.read()])
```

## Gotchas

-   **Model Availability**: Make sure you have run `ollama pull <model>` on the host machine before calling it from your API.
-   **Concurrency**: Ollama handles its own queue, but it's still good practice to use the **GPU Semaphore** if you want to control exactly how many concurrent requests your FastAPI app sends to Ollama.
