from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class AppliedPattern(BaseModel):
    id: str
    version: str
    applied_at: datetime
    files_created: list[str]
    files_modified: list[str]
    env_vars_added: list[str]

class AllocatedPort(BaseModel):
    service: str
    port: int
    protocol: Literal["tcp", "udp"] = "tcp"

class ManifestV2(BaseModel):
    manifest_version: Literal["2", 2] = "2" # type: ignore
    nikame_version: str
    project_name: str
    created_at: datetime
    patterns_applied: list[AppliedPattern] = []
    ports_allocated: list[AllocatedPort] = []
    env_vars: list[str] = []
    last_verified: datetime | None = None
    verification_passed: bool | None = None
