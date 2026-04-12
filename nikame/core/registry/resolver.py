import networkx as nx
from pydantic import BaseModel

from .loader import RegistryLoader
from .schema import PatternManifest


class ResolutionResult(BaseModel):
    can_apply: bool
    install_order: list[str]  # Topological order
    missing_requirements: list[str]
    hard_conflicts: list[str]
    error_message: str | None = None


class RegistryResolver:
    """Orchestrates complex dependency resolution and topological sorting for patterns."""
    
    def __init__(self, loader: RegistryLoader) -> None:
        self.loader = loader

    def resolve(self, target_pattern_id: str, applied_pattern_ids: list[str]) -> ResolutionResult:
        """
        Resolves the full dependency chain for a pattern.
        Returns the order in which patterns must be applied.
        """
        all_patterns = self.loader.load_all()
        id_map: dict[str, PatternManifest] = {p.id: p for p in all_patterns}
        
        if target_pattern_id not in id_map:
            return ResolutionResult(
                can_apply=False,
                install_order=[],
                missing_requirements=[target_pattern_id],
                hard_conflicts=[],
                error_message=f"Target pattern '{target_pattern_id}' not found in registry."
            )

        # Build Dependency Graph
        # Note: We use a directed graph where A -> B means A depends on B
        graph: nx.DiGraph[str] = nx.DiGraph()
        to_process = [target_pattern_id]
        processed = set()
        
        hard_conflicts = []
        
        while to_process:
            pid = to_process.pop(0)
            if pid in processed:
                continue
                
            pattern = id_map.get(pid)
            if not pattern:
                # We'll treat this as a missing requirement later
                continue
                
            processed.add(pid)
            graph.add_node(pid)
            
            # Check for conflicts with already applied patterns OR patterns in the chain
            for conflict_id in pattern.conflicts:
                if conflict_id in applied_pattern_ids:
                    hard_conflicts.append(f"{pid} conflicts with already applied {conflict_id}")
            
            # Extract dependencies
            for dep_id in pattern.requires:
                # Special handling for wildcards (database.* -> database.postgres)
                # For Phase 4, we'll support direct IDs or simple prefix wildcards
                actual_dep_ids = self._resolve_wildcard(dep_id, id_map)
                
                if not actual_dep_ids:
                    return ResolutionResult(
                        can_apply=False,
                        install_order=[],
                        missing_requirements=[dep_id],
                        hard_conflicts=hard_conflicts,
                        error_message=f"Requirement '{dep_id}' (needed by '{pid}') cannot be satisfied."
                    )
                
                for actual_id in actual_dep_ids:
                    if actual_id != pid:
                        graph.add_edge(pid, actual_id)
                        to_process.append(actual_id)

        # Check for cycles
        try:
            # install_order should be the order of applying, so children first
            # nx.topological_sort for A depends on B (A->B) returns B before A if we use reverse or just logical order
            # The standard sort returns [B, A] for B <- A (meaning B must be before A)
            # networkx returns nodes so that for edge (u, v), u appears before v.
            # If A -> B (A depends on B), then [A, B]. But we need [B, A].
            # So we use the reverse graph.
            order = list(nx.topological_sort(graph.reverse()))
            
            # Filter out already applied patterns
            install_order = [pid for pid in order if pid not in applied_pattern_ids]
            
            return ResolutionResult(
                can_apply=len(hard_conflicts) == 0,
                install_order=install_order,
                missing_requirements=[],
                hard_conflicts=hard_conflicts
            )
        except nx.NetworkXUnfeasible:
            return ResolutionResult(
                can_apply=False,
                install_order=[],
                missing_requirements=[],
                hard_conflicts=[],
                error_message="Circular dependency detected in pattern registry."
            )

    def _resolve_wildcard(self, dep_id: str, id_map: dict[str, PatternManifest]) -> list[str]:
        """Resolves wildcards like 'database.*' to a list of available IDs."""
        if "*" in dep_id:
            prefix = dep_id.split("*")[0]
            # In a real system, we might ask the user which database to use.
            # For now, we'll pick the first one matching the prefix if it's a requirement.
            return [pid for pid in id_map.keys() if pid.startswith(prefix)][:1]
        return [dep_id] if dep_id in id_map else []
