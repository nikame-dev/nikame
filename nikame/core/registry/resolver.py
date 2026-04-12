from pydantic import BaseModel
from typing import List
from .loader import RegistryLoader

class ConflictResult(BaseModel):
    can_apply: bool
    missing_requirements: List[str]
    hard_conflicts: List[str]
    optional_suggestions: List[str]

class ConflictResolver:
    def __init__(self, loader: RegistryLoader):
        self.loader = loader

    def check_conflicts(self, target_pattern_id: str, applied_pattern_ids: List[str]) -> ConflictResult:
        pattern = self.loader.get_pattern(target_pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {target_pattern_id} not found in registry")
            
        missing_reqs = [req for req in pattern.requires if req not in applied_pattern_ids]
        hard_conflicts = [con for con in pattern.conflicts if con in applied_pattern_ids]
        optional_suggestions = [opt for opt in pattern.optional if opt not in applied_pattern_ids]
        
        return ConflictResult(
            can_apply=not missing_reqs and not hard_conflicts,
            missing_requirements=missing_reqs,
            hard_conflicts=hard_conflicts,
            optional_suggestions=optional_suggestions
        )
