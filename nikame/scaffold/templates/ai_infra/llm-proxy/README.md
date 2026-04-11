# LLM Proxy

A pattern for building an internal gateway to LLM providers (OpenAI, Anthropic, local vLLM).

## Why build a proxy?

1.  **Centralized Auth**: Your frontend calls your API, and your API injects the secret API keys.
2.  **Cost Tracking**: Log every request and response to track token usage per user.
3.  **Caching**: Implement Semantic Cache to save money on redundant queries.
4.  **Resilience**: Automatically failover between providers (e.g., if OpenAI is down, switch to Anthropic).

## Usage

1. Configure your API keys.
2. Mount the router:

```python
from app.routers.llm_proxy import router as proxy_router
app.include_router(proxy_router)
```

## How to use from Frontend

Point your OpenAI SDK to your server:

```javascript
const openai = new OpenAI({
  apiKey: 'N/A', // Your app handles auth
  baseURL: 'https://your-api.com/v1' 
});
```

## Gotchas

-   **Streaming Complexity**: Passing through SSE streams (Server-Sent Events) requires careful handling of HTTP chunks to avoid buffering mid-transit.
-   **Timeouts**: LLMs are slow. Ensure your proxy client has a sufficiently long timeout (60s+).
