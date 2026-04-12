import enum
import json
from pathlib import Path
from typing import Any, Protocol, cast

from nikame.copilot.context import ContextManager
from nikame.copilot.providers.base import LLMProvider
from nikame.core.ast.stubber import generate_stub
from nikame.core.diff import FileDiff, ProjectDiff
from nikame.engines.rollback import RollbackEngine
from nikame.engines.scaffold import ScaffoldEngine
from nikame.engines.verify import SyntaxVerifier


class AgentUI(Protocol):
    """Protocol for UI callbacks to keep the agent decoupled from the TUI."""
    async def on_state_change(self, state: "AgentState") -> None: ...
    async def on_thought(self, text: str) -> None: ...
    async def on_proposal(self, diff: ProjectDiff) -> bool: ... # Return True to proceed
    async def on_error(self, message: str) -> None: ...


class AgentState(enum.Enum):
    IDLE = "idle"
    PLANNING = "planning"
    REVIEWING = "reviewing"
    ACTING = "acting"
    VERIFYING = "verifying"
    SUCCESS = "success"
    ERROR = "error"


class AgentLoop:
    """
    The core autonomous loop of NIKAME.
    Orchestrates planning, acting, and verification.
    """

    def __init__(
        self,
        project_root: Path,
        provider: LLMProvider,
        ui: AgentUI | None = None
    ) -> None:
        self.project_root = project_root
        self.provider = provider
        self.ui = ui
        self.context = ContextManager(project_root)
        self.state = AgentState.IDLE
        self.current_plan: ProjectDiff | None = None

    async def _set_state(self, state: AgentState) -> None:
        self.state = state
        if self.ui:
            await self.ui.on_state_change(state)

    async def run_task(self, task: str) -> None:
        """Starts the autonomous loop for a given task."""
        try:
            # 1. PLANNING
            await self._set_state(AgentState.PLANNING)
            if self.ui:
                await self.ui.on_thought("Analyzing project context and planning changes...")
                
            system_prompt = self.context.build_system_prompt(task)
            
            response = await self.provider.complete(
                messages=[{"role": "user", "content": f"Propose a plan for: {task}"}],
                system=system_prompt,
                stream=False
            )
            
            # Parse structured LLM output (JSON)
            try:
                # Clean response if it contains markdown code blocks
                clean_response = str(response).strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:-3].strip()
                elif clean_response.startswith("```"):
                    clean_response = clean_response[3:-3].strip()
                
                plan_data = json.loads(clean_response)
                actions = []
                for action in plan_data.get("actions", []):
                    actions.append(FileDiff(**action))
                
                self.current_plan = ProjectDiff(
                    actions=actions, 
                    summary=plan_data.get("summary", "No summary provided")
                )
            except Exception as e:
                raise ValueError(f"Failed to parse agent plan: {e}\nResponse: {response}")
            
            # 2. REVIEWING
            await self._set_state(AgentState.REVIEWING)
            if self.ui:
                proceed = await self.ui.on_proposal(self.current_plan)
                if not proceed:
                    if self.ui:
                        await self.ui.on_thought("Plan rejected by user. Resetting.")
                    await self._set_state(AgentState.IDLE)
                    return

            # 3. ACTING
            await self._set_state(AgentState.ACTING)
            if self.ui:
                await self.ui.on_thought("Applying plan changes to filesystem...")
            
            snapshot_id = await self._execute_plan(self.current_plan)
            
            # 4. VERIFYING
            await self._set_state(AgentState.VERIFYING)
            if self.ui:
                await self.ui.on_thought("Running integrity checks...")
            
            verify_result = await self._verify_project()
            
            if verify_result.passed:
                await self._set_state(AgentState.SUCCESS)
                if self.ui:
                    await self.ui.on_thought("Task completed successfully!")
            else:
                if self.ui:
                    await self.ui.on_thought(f"Verification failed: {verify_result.cycles}. Rolling back.")
                
                rollback = RollbackEngine(self.project_root)
                rollback.restore_snapshot(snapshot_id)
                await self._set_state(AgentState.ERROR)
                if self.ui:
                    await self.ui.on_error("Verification failed. Changes rolled back.")
            
        except Exception as e:
            await self._set_state(AgentState.ERROR)
            if self.ui:
                await self.ui.on_error(str(e))

    async def _execute_plan(self, plan: ProjectDiff) -> str:
        """Executes the approved plan and returns a snapshot ID for rollback."""
        rollback = RollbackEngine(self.project_root)
        scaffold = ScaffoldEngine()
        
        # Determine affected files for snapshot
        affected_files = [self.project_root / action.path for action in plan.actions]
        snapshot_id = rollback.create_snapshot(affected_files, label=plan.summary[:20])
        
        for action in plan.actions:
            target_path = self.project_root / action.path
            
            if action.action == "create":
                scaffold.write_file(target_path, action.content or "", overwrite=True)
            elif action.action == "modify":
                # For modify, LLM provides full content or block
                # Production implementation would use ASTMerger here
                scaffold.write_file(target_path, action.content or "", overwrite=True)
            elif action.action == "inject":
                if action.marker:
                    scaffold.inject_into_file(target_path, action.marker, action.content or "")
            elif action.action == "delete":
                if target_path.exists():
                    target_path.unlink()
                    
        return snapshot_id

    async def _verify_project(self) -> Any:
        """Runs the SyntaxVerifier and returns the result."""
        verifier = SyntaxVerifier(self.project_root)
        return verifier.verify()
