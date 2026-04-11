import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Any, Dict, Optional

logger = logging.getLogger("app.ai_infra.hf_manual")

class HFModelManager:
    """
    Manages low-level Tokenizer and Model for fine-grained control.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None

    async def load(self):
        logger.info(f"Loading tokenizer and model: {self.model_name}...")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model on GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None
        )
        logger.info("Model and tokenizer loaded.")

    def generate(self, prompt: str, **gen_kwargs) -> str:
        """
        Synchronous generation call (should be run in executor if called from async).
        """
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                **gen_kwargs
            )
            
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
