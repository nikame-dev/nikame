from fastapi import APIRouter, Depends
from app.ai_infra.model_loader import get_model
from app.ai_infra.gpu_semaphore import get_gpu_lock
from app.ai_infra.single_inference import InferenceRequest, InferenceResponse, perform_inference

router = APIRouter(prefix="/ai", tags=["Inference"])

@router.post("/predict", response_model=InferenceResponse, dependencies=[Depends(get_gpu_lock)])
async def predict_single(
    request: InferenceRequest,
    model: Any = Depends(get_model)
):
    """
    Endpoint for single-item inference.
    Guarded by GPU semaphore to prevent OOM.
    """
    return await perform_inference(model, request)
