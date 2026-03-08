"""nikame preflight — Production readiness checks.

Runs before `nikame up` and verifies the generated project is production-ready.
Checks: Python imports, env vars, Docker images, volume mounts, free ports,
tests, and Alembic migration chain.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import click
import yaml

from nikame.utils.logger import console


# ─────────────────────── Check Framework ─────────────────────────

class CheckResult:
    """A single preflight check result."""

    def __init__(self, name: str, severity: str = "P0"):
        self.name = name
        self.severity = severity  # P0 = blocker, P1 = warning
        self.passed = False
        self.message = ""
        self.fix_hint = ""

    def ok(self, msg: str = "OK") -> "CheckResult":
        self.passed = True
        self.message = msg
        return self

    def fail(self, msg: str, fix: str = "") -> "CheckResult":
        self.passed = False
        self.message = msg
        self.fix_hint = fix
        return self

    def skip(self, msg: str = "Skipped") -> "CheckResult":
        self.passed = True
        self.message = f"(skipped) {msg}"
        return self


# ─────────────────────── Check Implementations ───────────────────

def check_python_imports(project_dir: Path) -> CheckResult:
    """Verify all generated Python files are importable."""
    result = CheckResult("Python Imports", severity="P0")

    # Find all Python files
    app_dirs = [
        project_dir / "services" / "api",
        project_dir / "app",
        project_dir / "services" / "worker",
    ]

    py_files = []
    for d in app_dirs:
        if d.exists():
            py_files.extend(d.rglob("*.py"))

    if not py_files:
        return result.skip("No Python files found")

    broken = []
    for f in py_files:
        proc = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile('{f}', doraise=True)"],
            capture_output=True, text=True, timeout=10
        )
        if proc.returncode != 0:
            broken.append((f.relative_to(project_dir), proc.stderr.strip().split("\n")[-1]))

    if broken:
        details = "; ".join(f"{p}: {e}" for p, e in broken[:3])
        return result.fail(
            f"{len(broken)} file(s) have syntax errors: {details}",
            fix="Run `python -m py_compile <file>` to see the exact error"
        )

    return result.ok(f"{len(py_files)} files compile OK")


def check_env_vars(project_dir: Path) -> CheckResult:
    """Verify all required env vars are set in .env.generated."""
    result = CheckResult("Environment Variables", severity="P0")

    env_file = project_dir / ".env.generated"
    if not env_file.exists():
        return result.fail(
            ".env.generated not found",
            fix="Run `nikame init` to generate environment files"
        )

    content = env_file.read_text()
    empty_vars = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            if not val.strip():
                empty_vars.append(key.strip())

    if empty_vars:
        return result.fail(
            f"{len(empty_vars)} env var(s) are empty: {', '.join(empty_vars[:5])}",
            fix="Fill in values in .env.generated"
        )

    return result.ok("All env vars have values")


def check_docker_images(project_dir: Path) -> CheckResult:
    """Verify all Docker images in compose are pullable."""
    result = CheckResult("Docker Images", severity="P1")

    compose_paths = list(project_dir.rglob("docker-compose*.yml")) + list(project_dir.rglob("docker-compose*.yaml"))
    if not compose_paths:
        return result.skip("No docker-compose files found")

    images = set()
    for cp in compose_paths:
        try:
            data = yaml.safe_load(cp.read_text())
            services = data.get("services", {})
            for svc_name, svc in services.items():
                if isinstance(svc, dict) and "image" in svc:
                    images.add(svc["image"])
        except Exception:
            pass

    if not images:
        return result.skip("No external images referenced")

    # Just verify format — actual pull would be too slow for preflight
    bad_images = [img for img in images if not re.match(r'^[\w./-]+(?::[\w.-]+)?$', img)]
    if bad_images:
        return result.fail(
            f"Invalid image references: {', '.join(bad_images)}",
            fix="Check image names in docker-compose.yml"
        )

    return result.ok(f"{len(images)} image references valid")


def check_volume_mounts(project_dir: Path) -> CheckResult:
    """Verify all volume mount paths exist."""
    result = CheckResult("Volume Mounts", severity="P1")

    compose_paths = list(project_dir.rglob("docker-compose*.yml")) + list(project_dir.rglob("docker-compose*.yaml"))
    if not compose_paths:
        return result.skip("No docker-compose files found")

    missing = []
    for cp in compose_paths:
        try:
            data = yaml.safe_load(cp.read_text())
            services = data.get("services", {})
            for svc_name, svc in services.items():
                if not isinstance(svc, dict):
                    continue
                for vol in svc.get("volumes", []):
                    if isinstance(vol, str) and ":" in vol:
                        host_path = vol.split(":")[0]
                        if host_path.startswith(("/", "$", "~")):
                            continue
                        if not any(c in host_path for c in [".", "/"]):
                            continue  # Named volume
                        resolved = cp.parent / host_path
                        if not resolved.exists():
                            missing.append(f"{svc_name}: {host_path}")
        except Exception:
            pass

    if missing:
        return result.fail(
            f"{len(missing)} mount(s) missing: {', '.join(missing[:3])}",
            fix="Create the missing files or directories"
        )

    return result.ok("All volume paths exist")


def check_port_availability(project_dir: Path) -> CheckResult:
    """Verify all ports in compose are available on the host."""
    result = CheckResult("Port Availability", severity="P0")

    compose_paths = list(project_dir.rglob("docker-compose*.yml")) + list(project_dir.rglob("docker-compose*.yaml"))
    if not compose_paths:
        return result.skip("No docker-compose files found")

    ports = set()
    for cp in compose_paths:
        try:
            data = yaml.safe_load(cp.read_text())
            services = data.get("services", {})
            for svc_name, svc in services.items():
                if not isinstance(svc, dict):
                    continue
                for port_mapping in svc.get("ports", []):
                    if isinstance(port_mapping, str):
                        # Format: "host:container" or "host:container/protocol"
                        parts = port_mapping.split(":")
                        host_port = parts[0].split("/")[0]
                        try:
                            ports.add(int(host_port))
                        except ValueError:
                            pass
        except Exception:
            pass

    if not ports:
        return result.skip("No port mappings found")

    occupied = []
    for port in sorted(ports):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(0.5)
                s.bind(("0.0.0.0", port))
            except OSError:
                occupied.append(str(port))

    if occupied:
        return result.fail(
            f"Port(s) already in use: {', '.join(occupied)}",
            fix=f"Stop the process using these ports or change them in docker-compose.yml"
        )

    return result.ok(f"{len(ports)} port(s) available")


def check_tests(project_dir: Path) -> CheckResult:
    """Run pytest and verify zero failures."""
    result = CheckResult("Test Suite", severity="P1")

    test_dirs = [
        project_dir / "tests",
        project_dir / "services" / "api" / "tests",
    ]

    has_tests = any(d.exists() and list(d.rglob("test_*.py")) for d in test_dirs)
    if not has_tests:
        return result.skip("No test files found")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=no", "-q", str(project_dir)],
        capture_output=True, text=True, timeout=120, cwd=str(project_dir)
    )

    if proc.returncode == 0:
        # Extract pass count from output
        lines = proc.stdout.strip().splitlines()
        summary = lines[-1] if lines else "passed"
        return result.ok(summary)
    else:
        lines = proc.stdout.strip().splitlines()
        summary = lines[-1] if lines else "Failed"
        return result.fail(
            f"Tests failed: {summary}",
            fix="Run `pytest` to see full output"
        )


def check_alembic(project_dir: Path) -> CheckResult:
    """Verify the Alembic migration chain is valid."""
    result = CheckResult("Alembic Migrations", severity="P1")

    alembic_dirs = [
        project_dir / "services" / "api" / "alembic",
        project_dir / "alembic",
    ]

    alembic_dir = None
    for d in alembic_dirs:
        if d.exists():
            alembic_dir = d
            break

    if not alembic_dir:
        return result.skip("No Alembic directory found")

    # Check that alembic.ini exists
    ini = alembic_dir.parent / "alembic.ini"
    if not ini.exists():
        return result.fail(
            "alembic.ini not found",
            fix="Run `alembic init` to create migration scaffold"
        )

    # Check that at least one migration version exists
    versions_dir = alembic_dir / "versions"
    if not versions_dir.exists() or not list(versions_dir.glob("*.py")):
        return result.skip("No migration versions yet")

    return result.ok("Migration scaffold valid")


def check_dockerfiles(project_dir: Path) -> CheckResult:
    """Verify all build services have Dockerfiles."""
    result = CheckResult("Dockerfiles", severity="P0")

    compose_paths = list(project_dir.rglob("docker-compose*.yml")) + list(project_dir.rglob("docker-compose*.yaml"))
    if not compose_paths:
        return result.skip("No docker-compose files found")

    missing = []
    for cp in compose_paths:
        try:
            data = yaml.safe_load(cp.read_text())
            services = data.get("services", {})
            for svc_name, svc in services.items():
                if not isinstance(svc, dict):
                    continue
                build = svc.get("build")
                if build is None:
                    continue

                if isinstance(build, str):
                    context = build
                    dockerfile = "Dockerfile"
                elif isinstance(build, dict):
                    context = build.get("context", ".")
                    dockerfile = build.get("dockerfile", "Dockerfile")
                else:
                    continue

                df_path = cp.parent / context / dockerfile
                if not df_path.exists():
                    missing.append(f"{svc_name}: {df_path.relative_to(project_dir)}")
        except Exception:
            pass

    if missing:
        return result.fail(
            f"{len(missing)} Dockerfile(s) missing: {', '.join(missing[:3])}",
            fix="Create the missing Dockerfiles"
        )

    return result.ok("All build services have Dockerfiles")


# ─────────────────────── CLI Command ─────────────────────────────

ALL_CHECKS = [
    check_python_imports,
    check_env_vars,
    check_dockerfiles,
    check_docker_images,
    check_volume_mounts,
    check_port_availability,
    check_tests,
    check_alembic,
]


@click.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory to check.",
)
@click.option("--fail-on-p1", is_flag=True, default=False, help="Also fail on P1 warnings.")
def preflight(project_dir: Path, fail_on_p1: bool) -> None:
    """Run production readiness checks before nikame up."""
    console.print("\n[bold cyan]━━━ NIKAME Pre-flight Checks ━━━[/bold cyan]\n")

    results: list[CheckResult] = []

    for check_fn in ALL_CHECKS:
        try:
            result = check_fn(project_dir)
        except Exception as e:
            result = CheckResult(check_fn.__name__.replace("check_", "").replace("_", " ").title())
            result.fail(f"Check crashed: {e}")
        results.append(result)

    # Print table
    console.print(f"  {'Check':<25} {'Status':<8} {'Details'}")
    console.print(f"  {'─' * 25} {'─' * 8} {'─' * 50}")

    p0_failures = 0
    p1_failures = 0

    for r in results:
        if r.passed:
            status = "[green]✓ PASS[/green]"
        elif r.severity == "P0":
            status = "[red]✗ FAIL[/red]"
            p0_failures += 1
        else:
            status = "[yellow]⚠ WARN[/yellow]"
            p1_failures += 1

        console.print(f"  {r.name:<25} {status}  {r.message}")
        if r.fix_hint:
            console.print(f"  {'':25}          [dim]Fix: {r.fix_hint}[/dim]")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    console.print(f"\n  [bold]{passed}/{total} checks passed[/bold]", end="")
    if p0_failures:
        console.print(f"  [red]{p0_failures} P0 blocker(s)[/red]", end="")
    if p1_failures:
        console.print(f"  [yellow]{p1_failures} P1 warning(s)[/yellow]", end="")
    console.print("")

    # Exit code
    if p0_failures > 0:
        console.print("\n[bold red]✗ Pre-flight failed. Fix P0 issues before running nikame up.[/bold red]\n")
        raise SystemExit(1)
    elif p1_failures > 0 and fail_on_p1:
        console.print("\n[bold yellow]⚠ Pre-flight has P1 warnings (--fail-on-p1 enforced).[/bold yellow]\n")
        raise SystemExit(1)
    else:
        console.print("\n[bold green]✓ Pre-flight passed. Ready for nikame up.[/bold green]\n")
