# Set up or adopt a handbook

## Before creating anything

Create neither the workspace nor the area: if one is missing, say so and stop. Where the area already has a handbook, write only what the request asks for and the handbook lacks. A folder without a marker is adopted only on request, within the scope asked. When adopting, keep the owner's content, and settle conflicting conventions and duplicate or malformed markers before changing them.

## Layout

```text
<area>/handbook/
  README.md
  practices/<name>.md
  checks/<name>.md
  playbooks/<name>/playbook-<name>.md
```

Create the README, which creates the folder, and only the folders the request needs; a handbook with only a README is valid. Add no filler guidance or scripts. If the request also asks for guidance, go on to its references. Setup alone calls for no review of what the handbook already holds. It changes no other handbook's README: report what those now lack.

## The README

Adapt [this skill's README starter](../assets/handbook-readme.md), titled for the area. The README says what the handbook is for, its workspace and area (links to the two folders), the handbooks that also apply (each one in a folder above the area, up to the workspace root), where the area's work is kept, inside the area or not, and where each piece of guidance is, linking only what exists. Given no purpose, describe the area's work from its files and say in the report that you did. A handbook with no guidance yet says so.

Keep every point of the starter's account of how to use the handbook, its paragraph on findings and saved reports included, in words that fit: a reader must need neither this skill nor the setup conversation. Do not reproduce the methodology or present this skill's limits as rules for ordinary work. Put the account in a separate linked file only when its length or an existing file makes that useful. A later rewrite of the README follows this section alone.

## The marker

The README carries exactly one marker, on a line of its own near the top:

```html
<!-- trellis:handbook {"format":1,"workspace":"../.."} -->
```

`workspace` is the relative path from the handbook to the workspace: one `..` for the handbook folder and one more for each folder between the area and the workspace root. That is `..` when the area is the workspace, `../..` one folder down, `../../..` two down. `format` is always `1`. The marker identifies a handbook; it does not make every file in the folder the handbook's.

Write a marker only after checking that its path leads to the workspace. Correct one that disagrees with where the handbook is when the request includes handbook edits; otherwise report it.

## The pointer

Setup and adoption end with the [report](../SKILL.md#report), which holds the pointer text to give the user.
