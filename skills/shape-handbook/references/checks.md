# Write a Check

A Check states an expectation for work and how to verify it. It applies whenever its conditions hold, with or without a Playbook. Verifying may take judgment. A tool can support a Check without making its judgment; a Check that needs one points to a script in a Playbook and keeps no script of its own.

## What a Check says

Write `checks/<name>.md` with headings that suit the expectation. It says when it applies and what it excludes, the one requirement to judge, how to verify it, and what each outcome means; [this skill's Check starter](../assets/check.md) has a prompt for each.

Pass needs evidence that the expectation is met. Fail needs evidence that it is not. Unable means that missing access, evidence or clarity prevents a supported conclusion. Not applicable means the conditions do not hold. Fit these meanings to the Check, each with its reason and what to do next; the labels alone are not enough.

Link a Practice for the reason behind a Check, and the work's requirement for its exact meaning. When the request also needs a Practice changed, change both.

## Findings, status and overlap

Say where saved findings belong without requiring a report from a task that asked for findings in the response: a storage convention adds nothing to what a task was asked to produce or allowed to write.

Fit the Check to the work's stated status. A precise open question can complete a draft while the decision behind it stays open. A readiness Check applies when someone claims readiness, not at every stage before that.

Merge Checks whose conditions and meaning of failure cannot be told apart, and keep separate the ones that can. Before finishing, ask whether a later reviewer could explain each outcome from evidence.
