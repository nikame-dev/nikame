import pytest
from typing import Any
from pathlib import Path
from nikame.copilot.agent import AgentLoop, AgentState, AgentUI
from nikame.copilot.context import ContextManager
from nikame.copilot.providers.base import LLMProvider
from nikame.core.diff import ProjectDiff, FileDiff
from unittest.mock import AsyncMock, MagicMock

# --- Context Tests ---

def test_context_ranking(tmp_path):
    """Verifies that ContextManager ranks files correctly based on task."""
    root = tmp_path
    (root / "app").mkdir()
    (root / "app" / "api").mkdir(parents=True)
    (root / "app" / "models").mkdir(parents=True)
    
    auth_py = root / "app" / "api" / "auth.py"
    auth_py.write_text("class Auth: ...")
    
    db_py = root / "app" / "models" / "database.py"
    db_py.write_text("class DB: ...")
    
    ctx = ContextManager(root)
    # Task about auth should rank auth.py higher
    context_str = ctx.get_full_context(task="authentication logic")
    
    assert "auth.py" in context_str
    # Simple check that it prioritizes
    auth_index = context_str.find("auth.py")
    db_index = context_str.find("database.py")
    assert auth_index < db_index

def test_context_token_budget(tmp_path):
    """Verifies that ContextManager respects token limits."""
    root = tmp_path
    for i in range(10):
        f = root / f"file_{i}.py"
        f.write_text("class A: pass\n" * 100)
    
    ctx = ContextManager(root)
    # Very small budget
    context_str = ctx.get_full_context(max_tokens=50)
    assert "[Context truncated" in context_str

# --- Agent Tests ---

class MockProvider(LLMProvider):
    async def complete(self, messages, system, stream=False):
        return '{"summary": "test plan", "actions": []}'
    
    @property
    def model_name(self) -> str: return "test-model"
    @property
    def max_context_tokens(self) -> int: return 4000
    async def health_check(self) -> Any: return None

@pytest.mark.asyncio
async def test_agent_loop_success(tmp_path):
    """Verifies that AgentLoop flows through PLANNING -> SUCCESS."""
    root = tmp_path
    provider = AsyncMock(spec=LLMProvider)
    provider.complete.return_value = '{"summary": "Add feature", "actions": []}'
    
    ui = MagicMock(spec=AgentUI)
    ui.on_proposal.return_value = True # User accepts plan
    
    agent = AgentLoop(root, provider, ui)
    await agent.run_task("Add something")
    
    assert agent.state == AgentState.SUCCESS
    ui.on_state_change.assert_any_call(AgentState.PLANNING)
    ui.on_state_change.assert_any_call(AgentState.SUCCESS)

@pytest.mark.asyncio
async def test_agent_loop_rollback(tmp_path):
    """Verifies that AgentLoop rolls back on verification failure."""
    root = tmp_path
    (root / "app.py").write_text("print('hello')")
    
    provider = AsyncMock(spec=LLMProvider)
    # Plan that 'modifies' app.py
    provider.complete.return_value = '{"summary": "Broken change", "actions": [{"path": "app.py", "action": "modify", "content": "INVALID SYNTAX ["}]}'
    
    ui = MagicMock(spec=AgentUI)
    ui.on_proposal.return_value = True
    
    agent = AgentLoop(root, provider, ui)
    await agent.run_task("Break it")
    
    # It should be in ERROR state after rollback
    assert agent.state == AgentState.ERROR
    # Original content should be restored
    assert (root / "app.py").read_text() == "print('hello')"
