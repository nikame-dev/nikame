import shutil
import time
from pathlib import Path

from nikame.core.errors import RollbackError


class RollbackEngine:
    """Handles project snapshots and rollbacks to ensure safe mutations."""
    
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.snapshots_dir = project_root / ".nikame" / "snapshots"

    def create_snapshot(self, affected_files: list[Path], label: str = "") -> str:
        """
        Creates a snapshot of the given files before they are modified.
        Returns the snapshot ID (timestamped).
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snap_{timestamp}"
        if label:
            snapshot_id += f"_{label.replace(' ', '_')}"
            
        snapshot_path = self.snapshots_dir / snapshot_id
        snapshot_path.mkdir(parents=True, exist_ok=True)
        
        for file_path in affected_files:
            if not file_path.exists():
                continue
                
            # Create relative path structure within snapshot
            rel_path = file_path.relative_to(self.project_root)
            dest_path = snapshot_path / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(file_path, dest_path)
            
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> list[Path]:
        """
        Restores a project to the state of the given snapshot.
        Returns a list of files that were restored.
        """
        snapshot_path = self.snapshots_dir / snapshot_id
        if not snapshot_path.exists():
            raise RollbackError(f"Snapshot {snapshot_id} not found.")
            
        restored_files = []
        # Walk through snapshot and copy files back to project root
        for src_path in snapshot_path.rglob("*"):
            if src_path.is_file():
                rel_path = src_path.relative_to(snapshot_path)
                dest_path = self.project_root / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(src_path, dest_path)
                restored_files.append(dest_path)
                
        return restored_files

    def list_snapshots(self) -> list[str]:
        """Returns a list of available snapshot IDs."""
        if not self.snapshots_dir.exists():
            return []
        return sorted([d.name for d in self.snapshots_dir.iterdir() if d.is_dir()], reverse=True)
