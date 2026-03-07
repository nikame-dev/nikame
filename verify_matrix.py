import sys
import logging
from dataclasses import dataclass

# Setup basic logging to see matrix engine output
logging.basicConfig(level=logging.DEBUG)

# Mock Nikame blueprint/config
@dataclass
class MockConfig:
    scale: str = "large"
    access_pattern: str = "read_heavy"
    features: list[str] = None
    
    def __post_init__(self):
        self.features = ["auth"]

@dataclass
class MockModule:
    NAME: str

@dataclass
class MockBlueprint:
    modules: list[MockModule]
    
class MockWriter:
    def write_file(self, *args, **kwargs): pass

from nikame.codegen.integrations.matrix import MatrixEngine

def run_test():
    print("--- Starting MatrixEngine Phase 1 Test ---")
    config = MockConfig()
    blueprint = MockBlueprint(modules=[
        MockModule("postgres"), 
        MockModule("dragonfly"),
        MockModule("fastapi")
    ])
    writer = MockWriter()
    
    engine = MatrixEngine(config, blueprint, writer)
    
    # We should see:
    # 1. Profile computed (Large, Read_heavy -> 100 conns, 86400 TTL)
    # 2. Ignored integration skipped (qdrant missing)
    # 3. Integration B triggers (requires postgres)
    # 4. Integration A triggers (requires postgres + dragonfly)
    # 5. Topological sort ensures B runs before A (since A depends on B)
    engine.execute()
    print("--- Test Complete ---")

if __name__ == "__main__":
    run_test()
