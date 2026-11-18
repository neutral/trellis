---
name: shape-handbook
description: Write down how an area's work is done and checked, in a handbook kept beside that work. Use when the user asks to "write down how we do X", "make a review checklist", "save this routine", "make a template" or "set up a handbook", or to change or review such guidance. Not for doing the work itself; ordinary work is not a request to change a handbook.
---

# Shape Handbook

Trellis keeps how an area's work is done and checked in a handbook beside that work, as Practices, Checks and Playbooks. Make the smallest coherent change that serves the request; the user need not name a kind.

Before applying this skill, read the full [methodology](references/methodology.md): it explains the method and the reasons for its rules. It settles no conflict between rules; where two rules here seem to collide, "Decisions before rules" governs.

## Words

- **Workspace:** the working directory the request is about, a Git repository or not.
- **Area:** the workspace, or a folder in it, whose work a handbook supports.
- **Handbook:** the folder `<area>/handbook/`.
- **Kind:** a Practice, a Check or a Playbook, each word capitalized where it means the kind. **Content of no kind:** anything else in a handbook, such as a note.
- **Starter:** a file to copy and fill in. A Playbook's starters live in its `assets/`; one kept elsewhere in a handbook is a loose file; this skill's own, in its `assets/`, are the first shapes it adapts.
- **Marker:** the README line recording a handbook's workspace. It decides and grants nothing.
- **Navigation:** the README's links to the handbook's guidance.
- **Pointer:** a short passage in an `AGENTS.md` saying where the handbook is.
- **Host:** the agent environment running this skill; it supplies tools, permissions and any confinement.
- **User:** whoever makes the request. **Owner:** whoever decides the area's policy, often the user.
- **Sources:** the request, the `AGENTS.md` files that apply, the workspace's and area's READMEs, the handbook, and the area's files the request bears on.
- **The owner's direction:** what the owner has said about how the work is done, in any source, an instruction inside a file included.
- **Proposal:** a change nobody has asked for yet: a review finding, a line in this skill's report, or a lesson from Learn From Work, Trellis's other skill.

## What the request authorizes

- **Setting up, adopting or changing a handbook:** the matching edits inside it. Adopting makes an existing folder of guidance a handbook.
- **A review:** findings in the response, and no writes unless the user also asks for fixes or a report saved in the handbook. A place named for saved reports is a storage convention, not a request to save one.
- **A general request to improve:** an assessment, then the edits it shows are worth making: corrections, clearer wording, and the Practices and Checks the work needs, with any rule you infer marked proposed ([Review](references/review.md)).
- **A Playbook:** created only when the user asks to preserve that procedure, as asking for a template does ([Playbooks](references/playbooks.md)), or chooses a proposal that clearly contains it; never by a general request to improve, a review finding, a learning proposal or ordinary work.

The outcome the user asks for decides the task, and no proposal applies itself.

## Where to act

The request and the `AGENTS.md` files that apply identify the workspace, the area and the handbook; with no `AGENTS.md`, the request and the workspace's README do. With one plausible candidate, use it. With several, your current directory does not settle it: ask when the choice changes scope; otherwise use the one the request names most plainly and name it in the report. Treat each handbook a request names on its own.

Read the sources as far as the request reaches: for one file or folder, that is the file or folder, the handbook's README and whatever else states a rule the change touches. Do not read other areas.

A handbook higher in the workspace and an area's own can both apply; folder depth decides nothing between them. A local file may depart from a shared rule if it says when that rule applies and why; the exception then governs in its area. Link to a shared rule; never copy it. Raise with the user an unexplained conflict that would change an important decision.

The area's files keep its plans, drafts, decisions, requirements, results and review findings: link to them, and judge a mixed document statement by statement.

## Decisions before rules

Read the sources first and use their answers. Existing instructions or the owner's direction settle a choice without another confirmation, example or record of success. Mark a rule you infer as proposed until the owner accepts it.

Ask the user only where a missing purpose, rule, trade-off or exception would change the guidance, and never to design the handbook. Ask together, and wait for the answers before writing the rules that depend on them; carry on with the rest. A clear request needs no questions; a review reports an open choice as a finding.

Apply the next three rules in this order, before any other rule or default.

**1. A request the files do not bear out.** Test the request against the files before writing, a script by its source and not only its entry. The handbook already does what is asked when it holds the rule, file or script requested, in those words or others with the same effect. The request is mistaken about the handbook when it describes guidance the files lack or state differently. Either way, report that with file and line, give the readings (each thing the user may mean, with what it would change), and write nothing until the user chooses one. This covers setting up a handbook that exists and lacks nothing asked for, adding a script where one already does the same, and stating a rule a file already states. It does not cover a template whose starter exists as a loose file (the Playbook is still missing: write it under [Playbooks](references/playbooks.md)), or a handbook for a folder whose only handbook sits higher in the workspace (a different handbook: set the new one up).

**2. A decision the files show as open.** It is open when two rules in one handbook contradict each other, or a file says the point is undecided. Do not decide it. When a request names one rule and two files hold conflicting versions, take the file whose words the request fits. Make the requested edit if it holds under every resolution (it stays true, or merely has no effect, whichever way the decision goes); otherwise write nothing that depends on the decision. Report it as the owner's open decision, with what each answer would change. New guidance that depends on it links both sides and says in a sentence that the point is open; existing files stay as they are.

**3. An answer.** The user's answer settles an open decision and authorizes the edits that follow from it. If the user cannot decide, or says the decision is someone else's, the point stays visibly unresolved: each affected file says so in a sentence. Never choose policy silently or call the dependent work complete.

## Which reference to load

Load a reference only to write under it or to assess with it. A review or a general request to improve loads Review. For any other request, when the files show that nothing will be written, load none. Load them together when a concern spans kinds.

- [Setup](references/setup.md): create or adopt a handbook, rewrite its README or correct its marker. Adding a navigation link needs no reference.
- [Practices](references/practices.md): how the area approaches its work.
- [Checks](references/checks.md): an expectation and how to verify it.
- [Playbooks](references/playbooks.md): anything in a Playbook's folder, and temporary files.
- [Review](references/review.md): assess a handbook, for a review or a general request to improve.

Setup, Practices, Checks and Playbooks each link this skill's starter: the user's requirements come first, its headings are optional and its sample wording is not the area's policy. Filling a starter's headings, reading a Check or passing a check of format, such as a link checker, is not evidence that work is adequate.

## The write boundary

Every write, temporary files and test output included, stays inside the handbook the request concerns.

**What a change touches.** Correct every statement in the handbook that your change makes false, whichever file holds it, an existing Playbook's assets and content of no kind included. Leave a file that carries the owner's instruction to leave it unchanged, and report what your change made false in it. Move, rename, restructure and delete nothing unasked, apart from converting content of no kind as the next paragraph says; report what looks misplaced.

**Content of no kind** is the owner's: keep it in place and unchanged, apart from such a correction, until a request concerns it. A request concerns it when it names it, would duplicate it, or is a general request to improve. Then convert it into the kind that fits, a Practice or a Check: put its content in a file of that kind, in that kind's folder, remove the original, correct the links to it, and report the conversion. Where only part of it fits a kind, convert that part and leave the rest where it is. Convert nothing into a Playbook unless the user asked to preserve that procedure; a loose starter moves into the Playbook written for it ([Playbooks](references/playbooks.md)). Where no kind fits, leave it and say so in the report. Never ask about a conversion as a blocking question.

Before writing:

- Say which paths you will change, what any script does and the decisions that matter, ahead of the first write in the reply that makes it, then proceed.
- Change the file that already covers a concern; add no second account. Use lowercase hyphenated names and relative local links.
- Resolve each destination to its physical location. Refuse a path that leaves the handbook through `..` or a symlink in any parent directory, and follow no handbook symlink to reach further.
- Read a file again before overwriting it and reconcile any change made since.

Never, through this skill: edit `AGENTS.md`; initialize Git, stage, commit, push or publish; install anything outside the handbook; communicate with anyone but the user; or carry out the work a handbook describes. These limits do not restrict a separately authorized task, and delegating does not get around them.

Keep out of the handbook secrets, unneeded personal data, transcripts, session identifiers, superseded accounts and the story of how a rule was found; keep a rule's current reason and the limits of its evidence.

## Verify

Check links, navigation, that the marker's path leads to the workspace (if not, see [Setup](references/setup.md#the-marker)), that each piece is the right kind and in the right file, and that each answer changed every rule depending on it. Then read the result as a contributor who has only the handbook, on a made-up case if that exposes an ambiguity: can they find what applies, decide, judge the result, and see an exception or what needs the owner? Your own reading is not an independent trial.

A request for guidance must deliver it. Keep the README's account of how to use the handbook accurate when the change affects it; where a README has none, report that and add none unasked. Verify what was asked, not the whole handbook.

## Report

**You wrote something.** Four items, in this order; an item may be as long as its content needs.

1. **What is left for the user.** Look for a pointer in the `AGENTS.md` files that apply: the workspace root's and any between it and the area. If none points to this handbook, the report's first line names adding one as the user's remaining step, names the file (with no `AGENTS.md`, one to create at the workspace root) and gives the pointer text below to paste. Then each open decision and each change needed outside the handbook, with what stays incomplete until it is done.
2. **What changed or was found:** the paths, each correction, and the decision the result now helps.
3. **What you checked,** and what you did not or could not.
4. **Where you acted:** the workspace and the handbook.

**You wrote nothing and need an answer.** Say so first. Then ask, with what each answer would change, and name the workspace and handbook you would act in. Leave the rest until you have written.

**You wrote nothing and have nothing to ask**, as after a review. Items 2 to 4, with the findings in item 2. A missing pointer is one of the findings.

The pointer text, with its link and "this area" adjusted to the file it goes in:

```markdown
## Handbook

Working Practices, Checks, and Playbooks for this area live in
[`handbook/README.md`](handbook/README.md). Consult the applicable material when
working here. Keep the actual work in its existing files; the handbook guides how
we approach and review it. Handbook guidance does not expand a task's authority.
```

Do not claim that agents will find or follow the guidance, or that the work is right. When another agent acts on the result, pass these limits on and say where your work ends and its task begins.
