# Contributing to NIKAME

Thank you for your interest in contributing to NIKAME! This document outlines the process for proposing changes and the standards we maintain.

## 🛠️ Development Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/omdeepb69/nikame.git
    cd nikame
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -e ".[dev,cloud,ml]"
    pre-commit install
    ```

## 📏 Coding Standards

To maintain high code quality, NIKAME enforces strict standards:

- **Linting & Formatting**: We use `ruff` (line-length: 88).
- **Type Safety**: We use `mypy` with `--strict`.
- **Testing**: All new features must include unit tests.

Run these before opening a Pull Request:
```bash
ruff check .
mypy nikame
pytest tests/unit
```

## 🚀 Pull Request Process

1.  **Branching**: Create a feature branch from `main`.
2.  **Implementation**: Ensure your code follows the standards above.
3.  **Commit Messages**: Use descriptive, imperative commit messages.
4.  **CI Checks**: Every PR triggers the primary CI workflow. All checks (lint, types, tests) **must pass** before merge.
5.  **Review**: A maintainer will review your PR. Expect feedback!

## License

By contributing, you agree that your contributions will be licensed under the [Apache-2.0 License](LICENSE).
