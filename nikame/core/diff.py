from typing import Literal

from pydantic import BaseModel


class FileDiff(BaseModel):
    """Represents a single file change within a project-wide diff."""
    path: str
    action: Literal["create", "modify", "delete", "inject"]
    content: str | None = None  # Full content for new files or injection
    marker: str | None = None   # Marker for injection
    diff: str | None = None     # Unified diff for modified files
    description: str | None = None


class ProjectDiff(BaseModel):
    """A collection of file changes representing a proposed operation."""
    actions: list[FileDiff]
    summary: str = ""

    def get_action_count(self, action_type: str) -> int:
        return len([a for a in self.actions if a.action == action_type])

    @property
    def total_changes(self) -> int:
        return len(self.actions)
