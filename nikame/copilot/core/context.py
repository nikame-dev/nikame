import os
import ast
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional

class StateManager:
    def __init__(self, root_dir: Path):
        self.path = root_dir / ".nikame_context"

    def load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except:
                return {}
        return {
            "project_name": "unknown",
            "architecture": "vertical-slice",
            "active_services": [],
            "installed_patterns": [],
            "integrity_status": "unknown"
        }

    def update(self, **kwargs):
        data = self.load()
        data.update(kwargs)
        self.path.write_text(json.dumps(data, indent=2))

class CopilotContext:
    def __init__(self, root_dir: Path = Path(".")):
        self.root_dir = root_dir.resolve()
        self.state = StateManager(self.root_dir)

    def build_system_prompt(self, registry_patterns: List[Any], mode: str = "fast") -> str:
        state = self.state.load()
        
        # Build available scaffolds
        available_scaffolds = "\n".join([f"- {p.slug} ({p.name})" for p in registry_patterns])
        
        return f"""You are NIKAME Agent (v1.3.2), an Autonomous Architect.
You must ACT, not talk. You are a machine that outputs execution tags.

YOUR ACTION TAGS:
1. [COMMAND: <command>] (e.g., [COMMAND: ls -al])
2. [SCAFFOLD: <slug>] (e.g., [SCAFFOLD: auth/api-key])
3. [WRITE: <file_path>] followed immediately by a markdown code block.

FEW-SHOT EXAMPLES (HOW YOU MUST RESPOND):
User: "Wire the rate limiter to main.py"
Assistant:
<thought>
I need to create main.py, import the rate limiter we scaffolded, and initialize FastAPI.
</thought>
[WRITE: main.py]
```python
from fastapi import FastAPI
from auth.rate_limiter import limiter

app = FastAPI()
app.state.limiter = limiter
```
MISSION_COMPLETE

CRITICAL RULES:
- PRIORITIZE VELOCITY: Always write the full implementation FIRST using dummy/placeholder credentials (e.g., `"MOCK_API_KEY"` or `"dummy_password"`).
- If a project is already scaffolded, DO NOT recreate the scaffolding logic manually. Just import it and wire it up in main.py.
- NEVER write code without the exactly formatted [WRITE: <path>] tag preceding it.
- NEVER output conversational text outside of <thought> blocks.

AVAILABLE SCAFFOLDS:
{available_scaffolds}

PROJECT STATE:
{json.dumps(state, indent=2)}
"""
