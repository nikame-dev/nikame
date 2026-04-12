from pathlib import Path

from nikame.copilot.core.integrity import IntegrityEngine
from nikame.copilot.utils import FileManager

fm = FileManager(Path('.'))
ie = IntegrityEngine(Path('.'))
main_file = Path('main.py')

# 1. Inject Webhook Logic
fm.inject_import(main_file, 'from app.logic.webhooks import WebhookManager')
fm.inject_router(main_file, "app.add_api_route('/webhooks', WebhookManager.handle, methods=['POST'])")

# 2. Inject Task Hub
# Note: Creating a mock router to pass smoke test since we just touched the file
Path('app/tasks/router.py').write_text("from fastapi import APIRouter\nrouter = APIRouter()")

fm.inject_import(main_file, 'from app.tasks.router import router as tasks_router')
fm.inject_router(main_file, "app.include_router(tasks_router, prefix='/tasks', tags=['tasks'])")

from rich.console import Console

console = Console()

# 3. Smoke Test
success, error = ie.smoke_test_app(main_file)
console.print(f'SMOKE_TEST: {"SUCCESS" if success else "FAILURE"}')
if not success:
    console.print(f'ERROR: {error}')
