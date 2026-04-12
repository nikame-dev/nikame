from typing import Literal

from pydantic import BaseModel, Field


class InjectRule(BaseModel):
    path: str
    operation: Literal["create", "append", "patch", "inject"]
    template: str | None = None
    content: str | None = None
    marker: str | None = None
    patch_target: str | None = None

class EnvVarDef(BaseModel):
    name: str
    description: str | None = None
    example: str | None = None
    default: str | None = None
    required: bool = False

class TestRule(BaseModel):
    template: str
    path: str

class PatternManifest(BaseModel):
    id: str
    version: str
    display_name: str
    description: str
    category: str = "uncategorized"
    tags: list[str] = Field(default_factory=list)
    author: str = "community"
    
    requires: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    
    injects: list[InjectRule] = Field(default_factory=list)
    migrations: list[str] = Field(default_factory=list)
    env_vars: list[EnvVarDef] = Field(default_factory=list)
    tests: list[TestRule] = Field(default_factory=list)
    
    docs_url: str | None = None
