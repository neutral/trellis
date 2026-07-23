"""Explicit invocation context and deterministic resource accounting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .diagnostics import FindingList, ResourceLimitError

if TYPE_CHECKING:
    from .filesystem import ReadBackend, ReadRoot

DEFAULT_MAX_FILE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 10_000
DEFAULT_MAX_DEPTH = 32
DEFAULT_MAX_FINDINGS = 5_000
DEFAULT_MAX_WORK_UNITS = 50_000
DEFAULT_MAX_OUTPUT_BYTES = 4 * 1024 * 1024
WORK_UNIT_BYTES = 1024


@dataclass(frozen=True)
class AuditLimits:
    """Deterministic ceilings for one audit invocation."""

    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_entries: int = DEFAULT_MAX_ENTRIES
    max_depth: int = DEFAULT_MAX_DEPTH
    max_findings: int = DEFAULT_MAX_FINDINGS
    max_work_units: int = DEFAULT_MAX_WORK_UNITS
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES


DEFAULT_LIMITS = AuditLimits()


@dataclass
class AuditBudget:
    """Track bounded read-only work without depending on wall-clock timing."""

    limits: AuditLimits
    total_bytes: int = 0
    entries: int = 0
    work_units: int = 0

    def charge_work(self, units: int = 1) -> None:
        if units < 0:
            raise ValueError("work units must not be negative")
        self.work_units += units
        if self.work_units > self.limits.max_work_units:
            raise ResourceLimitError("work-limit")

    def check_depth(self, depth: int) -> None:
        if depth > self.limits.max_depth:
            raise ResourceLimitError("depth-limit")

    def charge_bytes(self, size: int) -> None:
        if size > self.limits.max_file_bytes:
            raise ResourceLimitError("file-size-limit")
        self.total_bytes += size
        if self.total_bytes > self.limits.max_total_bytes:
            raise ResourceLimitError("total-size-limit")
        self.charge_work(max(1, math.ceil(size / WORK_UNIT_BYTES)))

    def charge_entry(self, depth: int) -> None:
        self.check_depth(depth)
        self.entries += 1
        self.charge_work()
        if self.entries > self.limits.max_entries:
            raise ResourceLimitError("entry-limit")


@dataclass
class AuditContext:
    """All mutable state and capabilities for one audit invocation."""

    root: ReadRoot
    budget: AuditBudget
    findings: FindingList

    @classmethod
    def open(
        cls,
        target: Path,
        limits: AuditLimits = DEFAULT_LIMITS,
        backend: ReadBackend | None = None,
    ) -> AuditContext:
        from .filesystem import ReadRoot

        budget = AuditBudget(limits)
        root = ReadRoot.open(target, budget=budget, backend=backend)
        return cls(
            root=root,
            budget=budget,
            findings=FindingList(limits.max_findings, limits.max_output_bytes),
        )
