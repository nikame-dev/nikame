# HF Transformers Manual

When the high-level `pipeline` API is too restrictive, use this pattern for direct access to `AutoModel` and `AutoTokenizer`.

## Features

-   **Fine-grained Control**: Access tokenizer settings (padding, truncation) and model generation parameters directly.
-   **Device Map**: Uses `device_map="auto"` to intelligently shard models across multiple GPUs if available.
-   **No Grad**: Enforces `torch.no_grad()` to ensure zero memory overhead from gradients during inference.

## Usage

Recommended for LLM applications requiring custom sampling parameters or KV-cache manipulation.

```python
# In your route
from fastapi import Depends
from app.ai_infra.hf_manual import HFModelManager

@app.post("/chat")
def chat(prompt: str, manager: HFModelManager = Depends(get_manager)):
    # Run in thread pool if sync
    return manager.generate(prompt, max_new_tokens=100, temperature=0.7)
```

## Gotchas

-   **KV Cache**: This basic pattern doesn't implement persistent KV caching between requests. Every call is a full re-computation of the prompt.
-   **Padding**: Always ensure `pad_token` is set if using batch inference.
