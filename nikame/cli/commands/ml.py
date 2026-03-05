import click

from nikame.mlops.hardware import HardwareDetector
from nikame.mlops.models import ModelManager
from nikame.utils.logger import console


@click.group(name="ml")
def ml_group() -> None:
    """MLOps and Model Management commands."""
    pass


@ml_group.command(name="info")
def ml_info() -> None:
    """Display detected hardware and model environment info."""
    hw = HardwareDetector.detect()

    console.print("\n[key]Hardware Capabilities:[/key]")
    console.print(f"  CPU Count: [info]{hw.cpu_count}[/info]")
    console.print(f"  System RAM: [info]{hw.ram_gb:.1f} GB[/info]")
    console.print(f"  GPU Type: [info]{hw.gpu_type}[/info]")
    if hw.gpu_type == "nvidia":
        console.print(f"  VRAM: [info]{hw.vram_gb:.1f} GB[/info] ({hw.gpu_count} GPUs)")
    elif hw.gpu_type == "apple":
        console.print("  Acceleration: [info]MPS (Metal Performance Shaders)[/info]")

    console.print("\n[key]Recommended Serving Backends:[/key]")
    if hw.gpu_type == "nvidia" and hw.vram_gb >= 16:
        console.print("  - LLMs: [success]vLLM[/success] (High throughput)")
    elif hw.gpu_type != "none":
        console.print("  - LLMs: [success]llama.cpp[/success] (GPU Accelerated)")
    else:
        console.print("  - LLMs: [warning]llama.cpp / AirLLM[/warning] (CPU Only)")


@ml_group.command(name="list")
def ml_list() -> None:
    """List downloaded models in cache."""
    manager = ModelManager()
    console.print(f"\n[key]Model Cache:[/key] {manager.cache_dir}")
    import os
    if not os.path.exists(manager.cache_dir):
        console.print("  [info]Cache is empty.[/info]")
        return
    models = os.listdir(manager.cache_dir)
    if not models:
        console.print("  [info]Cache is empty.[/info]")
    for m in models:
        console.print(f"  - {m}")
