from pathlib import Path
from typing import Any

import jinja2


class ScaffoldEngine:
    """Engine for rendering templates and injecting code into files."""

    def __init__(self) -> None:
        self.env = jinja2.Environment(
            loader=jinja2.DictLoader({}),  # Default empty, will be updated per call
            autoescape=jinja2.select_autoescape()
        )

    def render_template(self, template_content: str, context: dict[str, Any]) -> str:
        """Renders a Jinja2 template string with the provided context."""
        template = self.env.from_string(template_content)
        return template.render(context)

    def write_file(self, target_path: Path, content: str, overwrite: bool = False) -> bool:
        """Writes content to a file, ensuring parent directories exist."""
        if target_path.exists() and not overwrite:
            return False
            
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content)
        return True

    def inject_into_file(self, target_path: Path, marker: str, content: str) -> bool:
        """Simple marker-based injection for files where AST-patching isn't used."""
        if not target_path.exists():
            return False
            
        existing_content = target_path.read_text()
        if marker not in existing_content:
            return False
            
        new_content = existing_content.replace(marker, f"{marker}\n{content}")
        target_path.write_text(new_content)
        return True

    def prepare_diff(self, pattern: Any, context: dict[str, Any]) -> Any:
        # Use simple mock/placeholder for now as core.diff and core.registry/resolver are being integrated
        from nikame.core.diff import FileDiff, ProjectDiff
        
        actions = []
        for inj in pattern.injects:
            if inj.operation == "create":
                # Render content
                if inj.template:
                    content = self.render_template(inj.template, context)
                else:
                    content = inj.content or ""
                actions.append(FileDiff(path=inj.path, action="create", content=content))
            elif inj.operation == "inject":
                # For injection, we treat it as a 'patch' in the Diff system
                # but with NIKAME's semantic marker replacement logic
                content = inj.content or ""
                if inj.template:
                    content = self.render_template(inj.template, context)
                actions.append(FileDiff(path=inj.path, action="inject", content=content, marker=inj.marker))
        
        return ProjectDiff(actions=actions, summary=f"Add pattern {pattern.id}")
