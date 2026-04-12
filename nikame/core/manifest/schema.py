from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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
    manifest_version: Literal["2"] = "2"
    nikame_version: str
    project_name: str
    created_at: datetime
    patterns_applied: list[AppliedPattern] = []
    ports_allocated: list[AllocatedPort] = []
    env_vars: list[str] = []
    last_verified: datetime | None = None
    verification_passed: bool | None = None
