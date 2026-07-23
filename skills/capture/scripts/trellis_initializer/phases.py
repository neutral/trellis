"""Explicit transaction and entry state machines."""

from __future__ import annotations

from enum import StrEnum

from .errors import ErrorCode, SupportError


class TransactionPhase(StrEnum):
    NEW = "new"
    JOURNALED = "journaled"
    PREPARING = "preparing"
    PREPARED = "prepared"
    APPLYING = "applying"
    VERIFYING = "verifying"
    COMMITTED = "committed"
    CLEANING = "cleaning"
    COMPLETE = "complete"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    INCOMPLETE = "incomplete"


class EntryPhase(StrEnum):
    PLANNED = "planned"
    RECOVERY_READY = "recovery_ready"
    STAGE_READY = "stage_ready"
    APPLYING = "applying"
    APPLIED = "applied"
    VERIFIED = "verified"
    CLEANED = "cleaned"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    INCOMPLETE = "incomplete"


class RecoveryActionKind(StrEnum):
    """Durably recorded, restart-idempotent recovery effects."""

    RESTORE = "restore"
    REMOVE_CREATED = "remove_created"
    REMOVE_STAGE = "remove_stage"
    REMOVE_RECOVERY = "remove_recovery"
    REMOVE_DIRECTORY = "remove_directory"
    REMOVE_JOURNAL = "remove_journal"


TRANSACTION_TRANSITIONS: dict[TransactionPhase, frozenset[TransactionPhase]] = {
    TransactionPhase.NEW: frozenset({TransactionPhase.JOURNALED}),
    TransactionPhase.JOURNALED: frozenset(
        {TransactionPhase.PREPARING, TransactionPhase.ROLLING_BACK}
    ),
    TransactionPhase.PREPARING: frozenset(
        {TransactionPhase.PREPARED, TransactionPhase.ROLLING_BACK}
    ),
    TransactionPhase.PREPARED: frozenset(
        {TransactionPhase.APPLYING, TransactionPhase.ROLLING_BACK}
    ),
    TransactionPhase.APPLYING: frozenset(
        {TransactionPhase.VERIFYING, TransactionPhase.ROLLING_BACK}
    ),
    TransactionPhase.VERIFYING: frozenset(
        {TransactionPhase.COMMITTED, TransactionPhase.ROLLING_BACK}
    ),
    TransactionPhase.COMMITTED: frozenset({TransactionPhase.CLEANING}),
    TransactionPhase.CLEANING: frozenset(
        {TransactionPhase.COMPLETE, TransactionPhase.INCOMPLETE}
    ),
    TransactionPhase.COMPLETE: frozenset(),
    TransactionPhase.ROLLING_BACK: frozenset(
        {TransactionPhase.ROLLED_BACK, TransactionPhase.INCOMPLETE}
    ),
    TransactionPhase.ROLLED_BACK: frozenset(),
    TransactionPhase.INCOMPLETE: frozenset(),
}

ENTRY_TRANSITIONS: dict[EntryPhase, frozenset[EntryPhase]] = {
    EntryPhase.PLANNED: frozenset(
        {EntryPhase.RECOVERY_READY, EntryPhase.STAGE_READY, EntryPhase.ROLLING_BACK}
    ),
    EntryPhase.RECOVERY_READY: frozenset(
        {EntryPhase.STAGE_READY, EntryPhase.ROLLING_BACK}
    ),
    EntryPhase.STAGE_READY: frozenset({EntryPhase.APPLYING, EntryPhase.ROLLING_BACK}),
    EntryPhase.APPLYING: frozenset({EntryPhase.APPLIED, EntryPhase.ROLLING_BACK}),
    EntryPhase.APPLIED: frozenset({EntryPhase.VERIFIED, EntryPhase.ROLLING_BACK}),
    EntryPhase.VERIFIED: frozenset({EntryPhase.CLEANED, EntryPhase.ROLLING_BACK}),
    EntryPhase.CLEANED: frozenset(),
    EntryPhase.ROLLING_BACK: frozenset({EntryPhase.ROLLED_BACK, EntryPhase.INCOMPLETE}),
    EntryPhase.ROLLED_BACK: frozenset(),
    EntryPhase.INCOMPLETE: frozenset(),
}


def require_transaction_transition(
    current: TransactionPhase, next_phase: TransactionPhase
) -> None:
    if next_phase not in TRANSACTION_TRANSITIONS[current]:
        raise SupportError(
            f"invalid transaction transition: {current.value} -> {next_phase.value}",
            code=ErrorCode.TRANSITION,
        )


def require_entry_transition(current: EntryPhase, next_phase: EntryPhase) -> None:
    if next_phase not in ENTRY_TRANSITIONS[current]:
        raise SupportError(
            f"invalid entry transition: {current.value} -> {next_phase.value}",
            code=ErrorCode.TRANSITION,
        )
