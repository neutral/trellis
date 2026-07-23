# Privacy Policy

Effective July 22, 2026

## Scope

This policy applies to Trellis, a skills-only plugin published by Neutral
("the publisher"). It operates inside the supported AI agent host the
user selects. The publisher does not operate a Trellis backend service.

## Information Trellis Processes

Trellis processes information inside the selected host to identify reusable
ways of working, propose Playbooks or Actions, save approved local files, and
audit Trellis-managed support. Depending on the requested workflow, this may
include:

- the current conversation
- one or more exact prior chat or session IDs the user supplies and the host can
  retrieve under that user's account
- files and file metadata in work folders the user has authorized the host to
  access
- local Playbooks, Action contracts, plans, results, and audit findings

Trellis does not require fixed profile or account fields. User-selected
conversations and files may incidentally contain personal or confidential
information, including names, contact details, identifiers, customer or
employee information, or source material. Users should provide only what the
requested workflow needs.

Trellis does not independently list, search, or mine ambient conversation
history. A chat or session ID grants no work-folder access, and work-folder
access grants no conversation-history access. Capture may create or update only
the capture and support files described in a proposal the user approves.

When the user asks a file-changing Action to prepare a review plan, the local
runtime stores private state under `_handbook/_scratch/plans/`. A saved plan
may contain named input values, file paths and hashes, and exact
before-and-after file content needed for review, state checking, and recovery.
Plan files and their parent directories use owner-only permissions where the
platform supports them. Applying a plan or running a test may also create a new
per-use transaction, backup, or test directory under `_scratch/`; the runtime
attempts to remove it when the operation finishes and reports when cleanup or
rollback is incomplete. A Playbook or Trellis skill may likewise use a new
per-use `_scratch/work/` directory for approved intermediate output.

During an approved handbook initialization, the initializer first creates an
owner-private `.trellis-initialize-transaction.json` journal in the work-folder
root. This ephemeral journal contains only recovery metadata such as safe
relative managed paths, transaction phases, digests, sizes, modes, and
filesystem identities. It does not contain owner file content, absolute work-
folder paths, conversation material, environment data, or credentials. The
initializer removes the journal last after successful completion or recovery;
it retains the journal after an interruption or ambiguous cleanup so recovery
can fail closed.

Generated `_scratch/` content is ignored by the supplied Git policy, but ignore
rules are not a security boundary and do not prevent backup or file-sync tools
from copying it. Users should treat the directory as private work-folder data,
avoid placing secrets there, and review any tool that synchronizes ignored
files.

Users should select only the conversations and work-folder paths needed for the
task. Capture is instructed not to retain secrets or unrelated source content
in saved Playbooks or Actions.

## Information the Publisher Receives

The publisher does not receive work-folder content, conversation content, local
file paths, Action output, or usage analytics through Trellis. Trellis includes
no publisher-operated telemetry, advertising, cookies, or user-account system.

If a person emails `support@neutral.dev`, the publisher and its email provider
receive the sender's address, message, and any attachments the sender chooses
to include. The publisher uses that information only to answer the request and
meet applicable legal, security, or abuse-prevention obligations. The publisher
does not sell it or use it for advertising. Never send credentials. Do not send
private conversation content or work-folder files unless they are necessary for
the request.

## Hosts and External Services

The selected host processes the conversations and work-folder information
described above under the user's account, workspace configuration, terms, and
privacy policy. The publisher does not control the host's processing.

Installing or updating Trellis through a code host, marketplace, or installer
may send the requested repository or plugin identifier and ordinary connection
metadata to that service under its own privacy policy.

Trellis only permits Actions that operate on explicitly scoped local files;
network access is outside the Action model. The supplied runtime enforces this
boundary as defense in depth, not as an operating-system security sandbox.

If a separately approved dependency installation, package audit, or signature
verification runs, npm contacts the configured package registry. The registry
may receive direct and transitive package names and versions, audit or signature
metadata, ordinary connection metadata, and any registry authentication the
user has configured. Trellis does not intentionally add conversation or
work-folder content to those requests.

A Playbook may describe separately approved use of host-native external tools
around a local Action. Any information sent to those tools is determined by the
user's approved host interaction and is processed under the host's and external
service's own terms and privacy policies.

## Retention

Trellis stores no remote copy of conversation or work-folder content for the
publisher. The selected host retains conversations and other host-managed data
according to the user's account settings and the host's policies. Files saved
in a work folder remain there until the user changes or deletes them; removing
Trellis does not remove those files.

Saved Action plans remain under `_handbook/_scratch/plans/`, including after an
apply, until the user deletes them. Temporary work, transaction, backup, and
test state is removed when its creating process cleans up successfully but may
remain after an interruption or a reported cleanup or rollback failure. The
root-level initializer journal is removed after successful initialization or
recovery and may remain when recovery still requires review.

Privacy-request communications sent to `support@neutral.dev` are retained in the
publisher's active mailbox for up to 12 months after the request is resolved,
unless longer retention is required for legal, security, or abuse-prevention
reasons. The email provider may retain deleted copies in backups for the
provider's own documented retention period.

## User Control

Users control whether to install or remove Trellis, which exact conversations
and work folders to provide, and whether to approve, edit, or reject proposed
local changes. Dependency installation, Action testing or execution, and any
host-native external tool use require separate decisions. Users can delete
saved files directly, remove Action plans after they are no longer needed for
review or apply, inspect any reported recovery state, and manage host-retained
conversations through the controls provided by their selected host. A person
may email `support@neutral.dev` to request access to, correction of, or deletion
of their privacy-request communications, subject to applicable legal
obligations.

## Changes and Contact

The publisher may update this policy when Trellis's data practices change.
Material changes will be published in this repository with a revised effective
date. Privacy requests may be sent to `support@neutral.dev`.
