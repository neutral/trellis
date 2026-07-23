# Scratch

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
