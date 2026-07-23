"""Immutable boundary models for JSON and Action metadata."""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, TypeAlias, TypeGuard, overload

if TYPE_CHECKING:
    from .filesystem import RepoPath


class FrozenDict(Mapping[str, object]):
    """A read-only mapping with no mutating interface or retained source alias."""

    __slots__ = ("_values",)

    def __init__(
        self, values: Mapping[str, object] | Iterable[tuple[str, object]] = ()
    ) -> None:
        self._values: Mapping[str, object] = MappingProxyType(dict(values))

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


class FrozenList(Sequence[object]):
    """A read-only JSON sequence backed by an unaliased tuple."""

    __slots__ = ("_values",)

    def __init__(self, values: Iterable[object] = ()) -> None:
        self._values = tuple(values)

    @overload
    def __getitem__(self, index: int) -> object: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[object, ...]: ...

    def __getitem__(self, index: int | slice) -> object | tuple[object, ...]:
        return self._values[index]

    def __len__(self) -> int:
        return len(self._values)


FrozenJson: TypeAlias = None | bool | int | float | str | FrozenDict | FrozenList


def freeze_json(value: object) -> FrozenJson:
    """Recursively convert parser output into immutable boundary models."""
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return value
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, list):
        return FrozenList(freeze_json(item) for item in value)
    if isinstance(value, dict):
        return FrozenDict(
            ((freeze_json_key(key), freeze_json(item)) for key, item in value.items()),
        )
    raise TypeError("JSON parser produced an unsupported value")


def freeze_json_key(value: object) -> str:
    """Validate one parser-produced JSON object key."""
    if not isinstance(value, str):
        raise TypeError("JSON object key is not a string")
    value.encode("utf-8", errors="strict")
    return value


def is_json_object(value: object) -> TypeGuard[Mapping[str, object]]:
    """Narrow parsed or test-supplied JSON objects without exposing mutation."""
    return isinstance(value, (dict, FrozenDict))


def is_json_array(value: object) -> TypeGuard[Sequence[object]]:
    """Narrow parsed or test-supplied JSON arrays without accepting strings."""
    return isinstance(value, (list, FrozenList))


def json_fingerprint(value: object) -> object:
    """Build a deterministic, hashable key without thawing immutable JSON."""
    if is_json_object(value):
        return (
            "object",
            tuple((key, json_fingerprint(item)) for key, item in sorted(value.items())),
        )
    if is_json_array(value):
        return ("array", tuple(json_fingerprint(item) for item in value))
    if value is None or isinstance(value, (bool, int, float, str)):
        return ("value", type(value).__name__, value)
    return ("invalid", type(value).__name__)


@dataclass(frozen=True)
class EffectScope:
    """One validated static path or input reference from an Action manifest."""

    path: str | None = None
    input_name: str | None = None


class ActionManifest(FrozenDict):
    """Schema-validated Action document for downstream agreement checks."""

    @classmethod
    def from_validated_json(cls, value: Mapping[str, object]) -> ActionManifest:
        """Construct only after the manifest validator accepts the full schema."""
        return cls(value.items())

    @property
    def format_number(self) -> int | None:
        value = self.get("format")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    def dependency_versions(self) -> Mapping[str, str]:
        result: dict[str, str] = {}
        values = self.get("dependencies")
        if not is_json_array(values):
            return result
        for value in values:
            if not is_json_object(value):
                continue
            name = value.get("name")
            version = value.get("version")
            if isinstance(name, str) and isinstance(version, str):
                result[name] = version
        return result

    def effect_scopes(self, effect: str) -> tuple[EffectScope, ...]:
        effects = self.get("effects")
        values = effects.get(effect) if is_json_object(effects) else None
        if not is_json_array(values):
            return ()
        result: list[EffectScope] = []
        for value in values:
            if not is_json_object(value):
                continue
            path = value.get("path")
            input_name = value.get("input")
            result.append(
                EffectScope(
                    path=path if isinstance(path, str) else None,
                    input_name=input_name if isinstance(input_name, str) else None,
                )
            )
        return tuple(result)


def is_frozen_mapping(value: object) -> TypeGuard[FrozenDict]:
    return isinstance(value, FrozenDict)


@dataclass(frozen=True)
class CaptureLink:
    section: str
    target: RepoPath
    resolved: RepoPath
    line: int


@dataclass(frozen=True)
class ActionPage:
    path: RepoPath
    title: str | None
    method_confidence: str | None
    readiness: str | None
    lifecycle: str | None
    sections: Mapping[str, str]
    content: str


def immutable_sections(items: Iterable[tuple[str, str]]) -> Mapping[str, str]:
    """Build an immutable mapping without exposing parsed owner material mutably."""
    return MappingProxyType(dict(items))
