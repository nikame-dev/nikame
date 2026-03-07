import sys
from unittest.mock import patch, MagicMock
from rich.console import Console
from nikame.cli.wizard.interactive import run_wizard

# Mock questionary to simulate a 2-model project
# 1. Basics: my-app, local, local
# 2. Infra: postgres, mongodb, dragonfly, redpanda, traefik
# 3. Features: auth, fastapi, search, guide=True
# 4. Meta: saas, medium, read_heavy
# 5. Models: 
#    - User: email (str, req, uniq, idx), name (str, req)
#    - Post: title (str, req, idx), author (rel, many-to-one -> User)

mock_responses = [
    "my-app", "local", "local", # Basics
    ["postgres", "mongodb"], "dragonfly", "redpanda", "traefik", # Infra
    "fastapi", ["auth", "search"], True, # Features
    "saas", "medium", "read_heavy", # Meta
    "User", "email", "str", True, True, True, # Model User, field email
    "name", "str", True, False, False, # field name
    "", # finish User fields
    "Post", "title", "str", True, False, True, # Model Post, field title
    "author", "relationship", "User", "many-to-one", # field author
    "", # finish Post fields
    "", # finish models
    "Proceed" # Confirmation
]

def mock_ask(self, *args, **kwargs):
    if not mock_responses:
        return None
    res = mock_responses.pop(0)
    # print(f"Mocking response: {res}")
    return res

# We need to mock questionary.text().ask(), select().ask(), etc.
with patch("questionary.Question.ask", mock_ask), \
     patch("questionary.select", lambda *args, **kwargs: MagicMock(ask=lambda: mock_responses.pop(0))), \
     patch("questionary.text", lambda *args, **kwargs: MagicMock(ask=lambda: mock_responses.pop(0))), \
     patch("questionary.checkbox", lambda *args, **kwargs: MagicMock(ask=lambda: mock_responses.pop(0))), \
     patch("questionary.confirm", lambda *args, **kwargs: MagicMock(ask=lambda: mock_responses.pop(0))), \
     patch("nikame.cli.wizard.interactive.console.clear", lambda: None):
    
    config = run_wizard()
    print("\nFinal Config yielded to init.py:")
    import json
    print(json.dumps(config, indent=2))
