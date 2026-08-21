# Trellis Privacy

Trellis is a local Agent Skills package. It has no hosted backend, account system, analytics,
telemetry, or required network service.

## Session use

- Capture works from the user's explicit Playbook request and the project files needed to place
  or update that Playbook.
- Discover uses the current session by default or exact session IDs the user selects and the host
  can retrieve.
- Trellis does not enumerate, search, sample, or mine ambient conversation history.
- A selected session does not authorize access to files, services, or credentials mentioned in
  that session.
- Trellis does not persist session transcripts or session IDs in Playbooks.

## Project files

Init, Capture, and Audit inspect only the project-local scope needed for the requested operation.
Trellis-managed content consists of the selected Playbooks-root marker and index, marked
`PLAYBOOK.md` files, and internal `_cli` files that Trellis created. Other files remain owner
content.

Trellis does not send project files or session material to third parties. A host may provide its
own model, storage, logging, or connector behavior; review that host's privacy terms separately.

## Sensitive material

Do not put secrets, credentials, private keys, access tokens, unnecessary personal data, or
confidential customer content in reusable Playbooks or supporting tools. Generalize or omit
sensitive residue when a reusable method can be preserved without it.

Trellis-created internal tools select fixed local-file operations and contain no generated
executable source. The shared runtime has no environment-secret, network, shell, child-process,
creation, deletion, permission, publication, or remote authority. An explicitly requested
standalone script can have a broader owner-approved design, but that design is outside the
internal-tool profile.

## No automatic publication

Trellis does not stage, commit, push, publish, send messages, or expose a Playbooks collection.
A Playbook or path reference does not grant authority for those actions.
