# Trellis privacy

Trellis is a local Agent Skills package. It has no hosted backend, account system,
analytics, telemetry, or required network service. Agent hosts have their own
model processing, storage, logging, and permission behavior; their policies govern
those services.

Skills inspect the selected area and relevant sources for the requested handbook
work. Learn From Work uses the current conversation, exact selected sessions, or
explicitly supplied accounts of work and artifacts. It does not enumerate unselected
history. References to other files, services, or conversations do not authorize access.

Trellis skills write only within selected handbooks. A review-only request to Shape
Handbook writes nothing, and Learn From Work never writes. The skills do not send
messages, publish handbook content, or upload project material. They do not persist
conversation transcripts or session identifiers.

Reusable content must omit secrets, credentials, unnecessary personal data, and
confidential details left over from the source work. Preserve a method with
generalized examples or exact links to appropriately accessible sources. Do not copy sensitive source content merely
to make a handbook self-contained.

Optional Playbook scripts run in your workspace. A script's effects stay inside
the workspace unless its Playbook declares what it reaches outside: another folder,
a network service, a secret. A declaration grants nothing. Review generated code
and enforce its scope through the execution host. The [contract](CONTRACT.md) describes the distinction
between authoring a script and running it during work.
