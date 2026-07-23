"""Command-line adapter for preview, write, and explicit recovery."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .constants import MINIMUM_CPYTHON
from .errors import SupportError, stale_journal_error
from .filesystem import ReadRoot
from .planner import build_immutable_plan, print_agents_note, print_preview
from .transaction import WriteTransaction, recover


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or initialize Trellis handbook support without Git actions."
        )
    )
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help="Explicit work folder to inspect or initialize.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply the previewed changes. Without this flag, no files are written.",
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help=(
            "Inspect an unfinished initializer transaction. Add --write only after "
            "reviewing the recovery preview."
        ),
    )
    return parser.parse_args()


def runtime_error() -> str | None:
    if sys.implementation.name != "cpython" or sys.version_info < MINIMUM_CPYTHON:
        return "Trellis initializer requires CPython 3.11 or newer"
    return None


def main() -> int:
    unsupported = runtime_error()
    if unsupported is not None:
        print(f"error: {unsupported}", file=sys.stderr)
        return 2
    args = parse_args()
    try:
        root = ReadRoot.open(args.target)
        if args.recover:
            recover(root, write=args.write)
            return 0
        if root.journal_exists():
            raise stale_journal_error()
        plan = build_immutable_plan(root)
        if args.write:
            WriteTransaction(root, plan).run()
        else:
            print_preview(plan.entries, root.target)
        print_agents_note(root.target, root.backend)
    except SupportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("error: could not update Trellis support", file=sys.stderr)
        return 2
    return 0
