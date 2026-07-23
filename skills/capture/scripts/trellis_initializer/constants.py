"""Owned formats and closed managed-path definitions for the initializer."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

FORMAT_MARKER = "<!-- trellis-format: 2 -->"
HANDBOOK_START = "<!-- trellis:handbook:start -->"
HANDBOOK_END = "<!-- trellis:handbook:end -->"
SUGGESTED_AGENTS_LINE = (
    "When relevant, read [`_handbook/overview.md`](_handbook/overview.md) "
    "for project Playbooks and Actions."
)

HANDBOOK_BLOCK = f"""{HANDBOOK_START}
{FORMAT_MARKER}
## Playbooks

No playbooks have been captured yet.

## Actions

No actions have been captured yet.
{HANDBOOK_END}"""

NEW_OVERVIEW = f"""# Handbook

Work-folder ways of working for people and agents.

{HANDBOOK_BLOCK}
"""

SCRATCH_GITIGNORE = """# Scratch content is local and must never be committed.
*
!.gitignore
!README.md
"""

SCRATCH_README = """# Scratch

This directory is local, ignored working space for Trellis. A Playbook,
Trellis skill, or Action that needs temporary storage must use a new per-use
directory here. Do not use this directory itself or reuse another run's
directory.

Scratch content may include saved plans, intermediate output, test data, or
recovery material. Treat it as private work-folder data: do not commit,
publish, or share it, and avoid placing secrets here. Git ignore rules are not
a security boundary and do not prevent backup or file-sync tools from copying
the content.

The process that creates a per-use directory owns its cleanup. Temporary run
and test directories are removed when work finishes and cleanup succeeds.
Saved Action plans remain until deleted. Recovery material may remain after a
reported cleanup or rollback failure.

Review reported paths before deleting them. Deleting a saved plan prevents it
from being reviewed or applied; deleting recovery material may prevent manual
recovery. Commands such as `git clean -fdX` can erase ignored scratch content.
"""

MINIMUM_CPYTHON = (3, 11)
STAGE_TEMP_MARKER = ".trellis-stage-"
RECOVERY_TEMP_MARKER = ".trellis-recovery-"
TRANSACTION_TEMP_MARKERS = (STAGE_TEMP_MARKER, RECOVERY_TEMP_MARKER)
JOURNAL_SCHEMA = "trellis.initialize-transaction.v2"
# Keep the durable journal outside directories the transaction may need to
# remove. Rollback can then retain it through every other cleanup effect and
# remove it only after directory cleanup succeeds.
JOURNAL_RELATIVE = Path(".trellis-initialize-transaction.json")


class ManagedFile(Enum):
    """The complete set of owner-visible files this helper may change."""

    OVERVIEW = Path("_handbook/overview.md")
    SCRATCH_GITIGNORE = Path("_handbook/_scratch/.gitignore")
    SCRATCH_README = Path("_handbook/_scratch/README.md")

    @property
    def relative(self) -> Path:
        return self.value


MANAGED_FILES = tuple(item.relative for item in ManagedFile)
