from fastapi import APIRouter, Request
from app.ai_infra.llm_proxy import proxy_llm_request

router = APIRouter(prefix="/v1", tags=["Proxy"])

@router.post("/chat/completions")
async def chat_proxy(request: Request):
    """
    OpenAI-compatible proxy endpoint.
    Passes requests through to the actual provider while allowing internal tracking.
    """
    return await proxy_llm_request(request)
