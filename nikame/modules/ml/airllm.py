"""AirLLM Model Serving module."""

from __future__ import annotations
from nikame.modules.registry import register_module

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


@register_module
class AirLLMModule(BaseModule):
    """AirLLM Model Serving module.

    Configures an AirLLM container to run massive LLMs (like 70B parameters) 
    on single consumer GPUs by utilizing layer-wise inference.
    """

    NAME = "airllm"
    CATEGORY = "ml"
    DESCRIPTION = "AirLLM serving engine for large models on consumer GPUs"
    DEFAULT_VERSION = "latest"
    DEFAULT_PORT = 8000

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        self.port = config.get("port", self.DEFAULT_PORT)
        
        # Determine model
        self.model_id = config.get("path", "garage-bAInd/Platypus2-70B-instruct")

    def required_ports(self) -> dict[str, int]:
        """Requested AirLLM port."""
        return {"airllm": self.port}

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for AirLLM."""
        project = self.ctx.project_name
        
        # AirLLM typically requires a custom python script. 
        # We mount a generated wrapper script to serve it via FastAPI.
        return {
            "airllm": {
                "image": "python:3.11-slim",
                "restart": "unless-stopped",
                "ports": [f"{self.ctx.host_port_map.get('airllm', self.port)}:8000"],
                "environment": {
                    "MODEL_ID": self.model_id,
                    "PORT": "8000",
                },
                "volumes": [
                    "hf_cache:/root/.cache/huggingface",
                    "./infra/scripts/airllm_server.py:/app/server.py:ro"
                ],
                "command": "bash -c 'pip install airllm fastapi uvicorn pydantic && python /app/server.py'",
                # NVIDIA GPU Support (Highly Recommended for AirLLM)
                "deploy": {
                    "resources": {
                        "reservations": {
                            "devices": [
                                {
                                    "driver": "nvidia",
                                    "count": "all",
                                    "capabilities": ["gpu"]
                                }
                            ]
                        }
                    }
                } if self.config.get("gpu", False) is True else {},
                "networks": [
                    f"{project}_frontend",
                    f"{project}_backend",
                ],
                "healthcheck": self.health_check(),
                "labels": {
                    "nikame.module": "airllm",
                    "nikame.category": "ml",
                },
            }
        }

    def init_scripts(self) -> list[tuple[str, str]]:
        """Provide the FastAPI wrapper script for AirLLM."""
        script = f'''import os
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from airllm import AutoModel

app = FastAPI(title="AirLLM Serving API")
model_id = os.environ.get("MODEL_ID", "{self.model_id}")

print(f"Loading AirLLM model: {{model_id}}")
# MAX_LENGTH is kept small here for safety, can be configured
model = AutoModel.from_pretrained(model_id)

class GenerationRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 50

@app.post("/generate")
async def generate(req: GenerationRequest):
    input_text = [req.prompt]
    input_tokens = model.tokenizer(input_text, return_tensors="pt", return_attention_mask=False, truncation=False)
    
    generation_output = model.generate(
        input_tokens['input_ids'].cuda(), 
        max_new_tokens=req.max_new_tokens,
        use_cache=True, 
        return_dict_in_generate=True
    )
    
    output = model.tokenizer.decode(generation_output.sequences[0])
    return {{"generated_text": output}}

@app.get("/health")
def health():
    return {{"status": "ready", "model": model_id}}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
'''
        return [("airllm_server.py", script)]

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s architecture for AirLLM."""
        name = "airllm"
        image = "python:3.11-slim"

        manifests = [
            self.service_account(name),
            self.config_map(
                name=f"{name}-script",
                data={"server.py": self.init_scripts()[0][1]}
            ),
            self.deployment(
                name=name,
                image=image,
                port=8000,
                command=["bash", "-c", "pip install airllm fastapi uvicorn pydantic && python /app/server.py"],
                env={
                    "MODEL_ID": self.model_id,
                    "PORT": "8000",
                }
            ),
            self.service(name, port=8000, target_port=8000),
        ]
        
        # Attach the ConfigMap to the deployment
        deployment = manifests[2]
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        container["volumeMounts"] = [{"name": "script", "mountPath": "/app/server.py", "subPath": "server.py"}]
        deployment["spec"]["template"]["spec"]["volumes"] = [
            {"name": "script", "configMap": {"name": f"{name}-script"}}
        ]

        if self.ctx.domain:
            manifests.append(
                self.ingress(name, f"airllm.{self.ctx.domain}", service_port=8000)
            )

        return manifests

    def health_check(self) -> dict[str, Any]:
        """AirLLM API health check."""
        return {
            "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "120s", # AirLLM takes time to download large models
        }

    def env_vars(self) -> dict[str, str]:
        """Expose AirLLM URL to apps."""
        return {
            "AIRLLM_URL": f"http://airllm:{self.port}",
        }


