# Trellis Distribution Terms

Effective July 22, 2026

## Scope

These terms apply to Trellis, a skills-only plugin published by Neutral
("the publisher"). They explain the distribution and its operating boundaries;
they do not add conditions to the CC0 dedication.

Trellis operates inside the AI agent host selected by the user. Use of that
host and any separately selected third-party service is governed by its own
terms and policies.

## CC0 Dedication

Except where a file states otherwise, the publisher dedicates any copyright
and related rights it owns in Trellis's original code, documentation, and
assets to the public domain under [CC0 1.0 Universal](LICENSE). Receiving,
installing, or using Trellis creates no additional copyright-license
conditions. The dedication is permanent for each distributed copy.

CC0 does not waive or license trademark or patent rights. It also does not, by
itself, change rights in a user's conversations, existing work-folder content,
third-party material, or original user-created work. Unmodified files copied
from the Trellis distribution remain under CC0. The dedication does not
automatically apply to original Playbooks, Action logic, or other content
authored by a user, although portions copied from Trellis remain under CC0. The
publisher claims no ownership of user content merely because Trellis processes
it.

## Operation and User Decisions

Trellis proposes work-folder changes for review. The user decides whether to
approve, edit, or reject each proposal and remains responsible for reviewing
generated content, maintaining appropriate backups or version control, and
confirming authorization to use the selected conversations, files, tools, and
services.

An approval to save an Action is not approval to execute it. Review every
Action's declared local file scopes, inputs, outputs, dependencies, readiness,
and success conditions before authorizing a test or run. Dependency
installation, testing, execution, and any outward step require separate user
decisions.

Conforming Trellis Actions run through the supplied local runtime and operate
only on explicitly scoped local files. Network access, external programs or
shells, publication, communication, remote changes, deletion, access changes,
and consequential judgment are outside the Action model. A Playbook may
describe separately approved use of the user's host or third-party services
around a local Action. Code modified or run outside the supplied runtime is not
covered by the Action runtime's controls.

The supplied runtime controls are defense in depth and are not an
operating-system security sandbox.

Trellis may create private local plan, transaction, backup, test, and
intermediate state under the ignored `_handbook/_scratch/` working area. Git
ignore rules are not a backup, privacy, or security boundary. Approved handbook
initialization may also create a temporary metadata-only
`.trellis-initialize-transaction.json` recovery journal in the work-folder
root; it is removed last after successful completion or recovery. The
[Privacy Policy](PRIVACY.md) describes what this local state contains, how long
it remains, and the controls available to the user.

Trellis does not itself grant access to any work folder, repository, data,
system, or service or override applicable law or third-party rights.

## Third-Party Services

The selected host, Node.js, npm, package registries, installation tools, and
any host-native external tools are independent of the publisher and governed
by their own terms and policies. The publisher does not control or provide
those products and services.

## Privacy

Trellis's data handling and user controls are described in the
[Privacy Policy](PRIVACY.md).

## Availability

Trellis is provided without support, a service-level commitment, or a promise
of maintenance or future updates. The publisher may change or discontinue
future distribution, but doing so does not revoke the CC0 dedication for copies
already distributed.

## Warranty and Liability

The warranty and liability provisions in section 4 of the CC0 dedication apply
to the distributed work to the maximum extent permitted by law.

## Changes

The publisher may update these terms for future releases. Material changes will
be published in this repository with a revised effective date and do not add
conditions to previously distributed CC0 copies.

## Contact

Legal notices and questions about these terms may be sent to
`support@neutral.dev`. This contact does not create a support commitment or
service-level agreement.
