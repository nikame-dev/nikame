import ast
import subprocess
import sys
import yaml
import shutil # Added for cleanup
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

class IntegrityEngine:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def audit_resources(self) -> List[str]:
        conflicts = []
        compose_path = self.root_dir / "infra" / "docker-compose.yml"
        if not compose_path.exists():
             compose_path = self.root_dir / "docker-compose.yml"
             
        if compose_path.exists():
            try:
                data = yaml.safe_load(compose_path.read_text())
                services = data.get("services", {})
                ports = []
                for s_name, s_cfg in services.items():
                    s_ports = s_cfg.get("ports", [])
                    for p in s_ports:
                        host_port = str(p).split(":")[0]
                        if host_port in ports:
                            conflicts.append(f"Port conflict: {host_port} used by multiple services")
                        ports.append(host_port)
                    
                    # ── Hardware Audit ──
                    if "deploy" in s_cfg and "resources" in s_cfg["deploy"]:
                        # Check for NVIDIA container toolkit if GPU is requested
                        if not shutil.which("nvidia-smi"):
                            conflicts.append(f"GPU requested for service '{s_name}' but nvidia-smi not found on host.")
            except Exception as e:
                conflicts.append(f"Compose Audit Error: {str(e)}")
        return conflicts

    def validate_blueprint(self, path: Path) -> Tuple[bool, List[str]]:
        """Validate a nikame.yaml blueprint for high-fidelity constraints."""
        errors = []
        try:
            data = yaml.safe_load(path.read_text())
            # ── Extension Sync ──
            if "databases" in data and "postgres" in data["databases"]:
                ext = data["databases"]["postgres"].get("extensions", [])
                if "pgvector" in ext:
                    # In a real scenario, we check the generator's image selection
                    pass
            
            # ── MLOps GPU Check ──
            if "mlops" in data and "models" in data["mlops"]:
                for model in data["mlops"]["models"]:
                    if model.get("gpu") == "required":
                         if not shutil.which("nvidia-smi"):
                             errors.append(f"Model '{model['name']}' requires GPU but no NVIDIA driver detected.")
            
            return len(errors) == 0, errors
        except Exception as e:
            return False, [str(e)]

    def validate_syntax(self, file_path: Path) -> Tuple[bool, str]:
        try:
            res = subprocess.run([sys.executable, "-m", "py_compile", str(file_path)], capture_output=True, text=True)
            return (res.returncode == 0, res.stderr)
        except Exception as e:
            return False, str(e)

    def smoke_test_app(self, main_file: Path) -> Tuple[bool, str]:
        code = f"import sys\nfrom pathlib import Path\nsys.path.append(str(Path.cwd()))\ntry:\n    from {main_file.stem} import app\n    print('SUCCESS')\nexcept Exception as e:\n    print(e)\n    sys.exit(1)"
        try:
            res = subprocess.run([sys.executable, "-c", code], cwd=self.root_dir, capture_output=True, text=True, timeout=10)
            return (res.returncode == 0 and "SUCCESS" in res.stdout, res.stdout or res.stderr)
        except Exception as e:
            return False, str(e)

    def rollback(self, file_path: Path):
        bak_path = file_path.with_suffix(file_path.suffix + ".bak")
        if bak_path.exists():
            shutil.copy2(bak_path, file_path)
