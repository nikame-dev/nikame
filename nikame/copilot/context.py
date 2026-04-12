from pathlib import Path

from nikame.core.ast.stubber import generate_stub
from nikame.core.manifest.store import ManifestStore


class ContextManager:
    """Manages project context for LLM prompts, including AST stubs and manifests."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.manifest_store = ManifestStore(project_root)

    def get_project_summary(self) -> str:
        """Generates a high-level summary of the project state."""
        try:
            manifest = self.manifest_store.load()
            if not manifest:
                return "Project summary unavailable (no manifest found)."
            summary = f"Project: {manifest.project_name}\n"
            summary += f"Patterns applied: {', '.join([p.id for p in manifest.patterns_applied])}\n"
            return summary
        except Exception:
            return "Project summary unavailable (error loading manifest)."

    def get_full_context(self, task: str = "", max_tokens: int = 8000) -> str:
        """
        Generates a comprehensive context string containing stubs of source files 
        ranked by relevance to the task.
        """
        # Heuristic: 1 token as approx 4 characters
        max_chars = max_tokens * 4
        
        parts = []
        parts.append(self.get_project_summary())
        parts.append("\n--- SOURCE CODE STUBS ---\n")
        
        current_chars = len("\n".join(parts))
        
        # 1. Gather all files and calculate scores
        scored_files: list[tuple[float, Path]] = []
        task_keywords = set(task.lower().split()) if task else set()

        for py_file in self.project_root.rglob("*.py"):
            if any(p in str(py_file) for p in [".venv", "venv", ".git", "__pycache__", ".pytest_cache", "tests/"]):
                continue
            
            score = 0.0
            file_name_lower = py_file.name.lower()
            
            # Key-word matches in filename
            for kw in task_keywords:
                if kw in file_name_lower:
                    score += 10.0
            
            # Directory prioritization
            if "app/api" in str(py_file):
                score += 5.0
            if "models" in str(py_file):
                score += 3.0
            
            scored_files.append((score, py_file))

        # 2. Sort by score (highest first)
        scored_files.sort(key=lambda x: x[0], reverse=True)

        # 3. Add to context until budget hit
        for _, py_file in scored_files:
            stub = generate_stub(py_file)
            rel_path = py_file.relative_to(self.project_root)
            file_context = f"\n### File: {rel_path}\n{stub}\n"
            
            if current_chars + len(file_context) > max_chars:
                parts.append(f"\n[Context truncated due to token limit of {max_tokens}]\n")
                break
                
            parts.append(file_context)
            current_chars += len(file_context)
            
        return "\n".join(parts)

    def build_system_prompt(self, task: str) -> str:
        """Builds a system prompt for the agent based on the current context."""
        context = self.get_full_context()
        
        prompt = f"""
You are NIKAME, an autonomous AI coding agent. Your goal is to help build and maintain production-grade FastAPI applications.

--- PROJECT CONTEXT ---
{context}

--- TASK ---
{task}

--- GUIDELINES ---
1. You MUST follow the existing patterns and architecture seen in the stubs.
2. You output a structured JSON plan. Use the following schema:
{{
    "summary": "High-level summary of the changes",
    "actions": [
        {{
            "path": "relative/path/to/file.py",
            "action": "create|modify|delete|inject",
            "content": "Full content for 'create' or 'inject', or new code block for 'modify'",
            "marker": "Optional marker for 'inject' action",
            "description": "Short explanation of why this action is needed"
        }}
    ]
}}

3. For "modify" actions, provide the full code block to be injected or the full file content if it's a small file.
4. You MUST output ONLY the JSON object. No preamble, no markdown code blocks.
"""
        return prompt.strip()
