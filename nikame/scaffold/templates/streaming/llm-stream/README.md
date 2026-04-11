# LLM Streaming

A drop-in pattern for streaming responses from LLM providers (OpenAI, Anthropic) directly to your frontend via FastAPI's `StreamingResponse`.

## Usage

1. Add your API key to `.env` or during `fastcheat add`.
2. Mount the router:

```python
from app.routers.llm_stream import router as llm_router
app.include_router(llm_router)
```

## How it works

The pattern uses an `AsyncGenerator` to wrap the provider's streaming SDK. It formats the output as Server-Sent Events (SSE), making it easy to consume using the browser's `EventSource` API or `fetch` with stream readers.

## Gotchas

* **Timeout**: Ensure your proxy (Nginx, Cloudflare) doesn't kill long-lived connections.
* **Error Handling**: Errors middle-stream are hard to catch on the client side. We include a `[DONE]` marker to signify successful completion.
