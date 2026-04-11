import onnxruntime as ort
import logging
import numpy as np
from typing import Any, Dict, List, Optional

logger = logging.getLogger("app.ai_infra.onnx")

class ONNXModelManager:
    """
    Manages ONNX Runtime sessions for high-performance CPU/GPU inference.
    """
    def __init__(self, model_path: str = "{{ONNX_MODEL_PATH}}", use_gpu: bool = False):
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.session = None

    async def load(self):
        logger.info(f"Loading ONNX model: {self.model_path}...")
        
        providers = ['CPUExecutionProvider']
        if self.use_gpu:
            # Requires onnxruntime-gpu
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
        self.session = ort.InferenceSession(self.model_path, providers=providers)
        logger.info(f"ONNX session loaded with providers: {self.session.get_providers()}")

    def predict(self, input_dict: Dict[str, np.ndarray]) -> List[np.ndarray]:
        """
        Synchronous prediction.
        """
        return self.session.run(None, input_dict)
