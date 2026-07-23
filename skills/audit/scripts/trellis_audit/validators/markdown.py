"""Bounded Markdown structure view for Trellis contract parsing."""

from __future__ import annotations

import re

from ..context import AuditBudget, AuditContext

_FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})")
_CONTROL_COMMENT_RE = re.compile(
    r" {0,3}<!--\s*(?:"
    r"trellis-capture:\s*(?:playbook|action)\s+format=[0-9]+|"
    r"trellis-format:\s*[0-9]+|"
    r"trellis:handbook:(?:start|end)"
    r")\s*-->[ \t]*"
)


def markdown_structure_view(context: AuditContext | AuditBudget, content: str) -> str:
    """Mask code and ordinary comments while preserving offsets and newlines."""
    result = ["\n" if character == "\n" else " " for character in content]
    position = 0
    fence_character: str | None = None
    fence_length = 0
    in_html_comment = False
    budget = context.budget if isinstance(context, AuditContext) else context

    def mask(start: int, end: int) -> None:
        for offset in range(start, end):
            if content[offset] != "\n":
                result[offset] = " "

    while position < len(content):
        newline = content.find("\n", position)
        line_end = len(content) if newline == -1 else newline
        next_position = len(content) if newline == -1 else newline + 1
        content_end = (
            line_end - 1
            if line_end > position and content[line_end - 1] == "\r"
            else line_end
        )
        line = content[position:content_end]
        budget.charge_work()

        fence = _FENCE_RE.match(line)
        if fence_character is not None:
            fence_closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
                line,
            )
            if fence_closing is not None:
                fence_character = None
                fence_length = 0
            position = next_position
            continue
        if fence is not None:
            marker = fence.group("fence")
            fence_character = marker[0]
            fence_length = len(marker)
            position = next_position
            continue
        if line.startswith("\t") or line.startswith("    "):
            position = next_position
            continue

        result[position:content_end] = line
        if _CONTROL_COMMENT_RE.fullmatch(line) and not in_html_comment:
            position = next_position
            continue

        cursor = 0
        while cursor < len(line):
            if line[cursor] != "`":
                cursor += 1
                continue
            run_end = cursor + 1
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            marker = line[cursor:run_end]
            closing_index = line.find(marker, run_end)
            if closing_index == -1:
                cursor = run_end
                continue
            mask(position + cursor, position + closing_index + len(marker))
            cursor = closing_index + len(marker)

        cursor = 0
        while cursor < len(line):
            if in_html_comment:
                closing_index = line.find("-->", cursor)
                if closing_index == -1:
                    mask(position + cursor, content_end)
                    break
                mask(position + cursor, position + closing_index + 3)
                in_html_comment = False
                cursor = closing_index + 3
                continue
            opening = line.find("<!--", cursor)
            if opening == -1:
                break
            if "".join(result[position + opening : position + opening + 4]) != "<!--":
                cursor = opening + 4
                continue
            closing_index = line.find("-->", opening + 4)
            if closing_index == -1:
                mask(position + opening, content_end)
                in_html_comment = True
                break
            mask(position + opening, position + closing_index + 3)
            cursor = closing_index + 3

        position = next_position

    return "".join(result)
