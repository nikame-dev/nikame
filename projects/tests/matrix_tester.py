import os
import subprocess
import yaml
import sys
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    print(f"Running: {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
    output = []
    for line in process.stdout:
        print(line, end="")
        output.append(line)
    process.wait()
    return subprocess.CompletedProcess(cmd, process.returncode, "".join(output), "")

def main():
    # projects/tests/matrix_tester.py -> repo root is two levels up
    root_dir = Path(__file__).resolve().parents[2]
    out_dir = root_dir / "projects/tests/out"
    registry_dir = root_dir / "nikame-registry/official"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    templates = list(registry_dir.glob("*.yaml"))
    print(f"Found {len(templates)} templates in registry.")
    
    # Optional: Run only specific ones for debugging
    # templates = [t for t in templates if t.stem in ["ecommerce", "saas-starter"]]
    
    results = []
    
    for template in templates:
        name = template.stem
        project_name = f"test-{name}"
        project_path = out_dir / project_name
        
        print(f"\n--- Testing Template: {name} ---")
        
        if project_path.exists():
            shutil.rmtree(project_path)
            
        cmd = f"python3 -m nikame.cli.main init --config {template} --no-interactive --output {project_path}"
        res = run_command(cmd, cwd=root_dir)
        
        if res.returncode == 0:
            print(f"SUCCESS: {name}")
            results.append((name, True))
        else:
            print(f"FAILED: {name}")
            results.append((name, False))

    # Custom Setup - Fixed Profile
    print(f"\n--- Testing Custom Setup: hybrid-multi-db ---")
    custom_yaml_path = root_dir / "projects/tests/custom_hybrid.yaml"
    custom_config = {
        "version": "1.0",
        "name": "custom-hybrid-db",
        "description": "A custom setup with multiple databases and ML.",
        "project": {
            "type": "ml_app",
            "scale": "large"
        },
        "environment": {
            "target": "aws",
            "profile": "production" # Fixed from 'prod'
        },
        "api": {
            "framework": "fastapi"
        },
        "databases": {
            "postgres": {},
            "mongodb": {},
            "elasticsearch": {}
        },
        "cache": {
            "provider": "redis"
        },
        "mlops": {
            "serving": ["ollama", "bentoml"],
            "monitoring": ["evidently"]
        },
        "features": ["auth", "payments", "search_sync"]
    }
    
    with open(custom_yaml_path, "w") as f:
        yaml.dump(custom_config, f)
        
    project_path = out_dir / "test-custom-hybrid"
    if project_path.exists():
        shutil.rmtree(project_path)
        
    cmd = f"python3 -m nikame.cli.main init --config {custom_yaml_path} --no-interactive --output {project_path}"
    res = run_command(cmd, cwd=root_dir)
    
    if res.returncode == 0:
        print(f"SUCCESS: custom-hybrid-db")
        results.append(("custom-hybrid-db", True))
    else:
        print(f"FAILED: custom-hybrid-db")
        results.append(("custom-hybrid-db", False))

    print("\n\n=== FINAL MATRIX TEST SUMMARY ===")
    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {name}")
        if not success:
            all_passed = False
            
    if all_passed:
        print("\nAll matrix tests passed!")
        print("\n--- Running Pytest for regression check ---")
        # Use the same interpreter as this script so repo-root imports resolve
        pytest_res = run_command(
            f"{sys.executable} -m pytest tests/generation -v",
            cwd=root_dir,
        )
        if pytest_res.returncode == 0:
            print("Pytest PASSED!")
        else:
            print("Pytest FAILED!")
            all_passed = False
    else:
        print("\nSome tests failed. Investigation needed.")

    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
