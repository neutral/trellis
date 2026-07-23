# How Trellis Identifies Reusable Work

Trellis does not require you to prove a method by performing it in a chat first.
If you already know the Playbook or Action you want, ask Trellis to create it
and describe what you need. Trellis can also look for candidates in work you
select. This file explains both routes, the techniques behind them, and which
parts are Trellis's own product design.

## You Can Lead, Or Trellis Can Look

<!-- markdownlint-disable MD013 -->
| Starting point | What you provide | What Capture does |
| --- | --- | --- |
| **Direct direction** | A goal, rough routine, draft, or exact Playbook or Action | Treats your words as the design brief, checks the shape, boundaries, verification, conflicts, and safety, then shows a proposal |
| **Reflective discovery** | The current conversation or exact prior conversation IDs your agent host can retrieve | Reconstructs the selected work, looks for reusable decisions and mechanics, and shows the strongest bounded candidates |
| **Hybrid refinement** | A candidate plus selected conversational work | Keeps your requested design separate from evidence, surfaces conflicts instead of silently choosing, then refines according to your direction |
<!-- markdownlint-enable MD013 -->

A direct description is authoritative about what you want. It is not proof that
the method already works in varied situations. Capture therefore labels a new
directly specified method **Provisional** unless there is operational evidence
for broader use. A new Action is also **Draft** and **Untested**, regardless of
how complete its specification is.

You do not need to supply conversation IDs for direct direction. Capture should
ask for IDs only when you ask it to examine prior conversations and have not
identified them.

## The Capture Method

### 1. Bound the material

For direct direction, the design brief is your request and any material you
explicitly place in scope. Capture may inspect only the Trellis-managed support
needed to find an equivalent, conflict, or path collision. For reflective
discovery, Capture uses the current conversation by default or only the exact
prior conversations you name. When you name prior conversations, the current
conversation is not evidence unless you include it. Capture does not search
ambient history, inspect adjacent chats, or treat an old approval as present
permission to act.

This makes it clear where each part of the proposal came from: your stated
design, selected operational evidence, or a clearly labeled inference.

### 2. Reconstruct a real example—or specify the intended method

When discovering from completed work, Capture first separates distinct pieces
of work. It reconstructs the trigger, starting state, intended result,
constraints, decisions, actions, verification, exceptions, and provenance
before trying to generalize.

When you provide the method directly, Capture does not invent a work history.
It maps your description to those same operational questions and labels what
has not yet been validated.

This reflects ideas from
[cognitive task analysis](https://digital.ahrq.gov/health-it-tools-and-resources/evaluation-resources/workflow-assessment-health-it-toolkit/all-workflow-tools/cognitive-task-analysis),
which studies reasoning and information processing that ordinary task
descriptions can miss, and the
[Critical Decision Method](https://digital.ahrq.gov/health-it-tools-and-resources/evaluation-resources/workflow-assessment-health-it-toolkit/all-workflow-tools/critical-decision-method),
which examines a concrete incident through its timeline, decision points, cues,
and alternatives. The
[MITRE Cognitive Engineering Toolkit](https://www.mitre.org/news-insights/publication/cognitive-engineering-toolkit)
also informed the focus on anomalies, expert strategies, novice traps, and
conditions where normal procedures fail.

Capture is not performing a formal cognitive task analysis or Critical
Decision Method interview. A conversation is partial evidence, memory can be
incomplete, and a user may reasonably choose not to answer follow-up questions.
The practical lesson for Trellis is to expose uncertainty instead of filling it
with plausible fiction.

### 3. Look at the turning points, not only the polished ending

For reflective discovery, Capture pays particular attention to:

- a correction or rejected default;
- a hidden constraint that changed the path;
- a failed attempt and the reason it failed;
- a cue that distinguished two plausible choices;
- an exception, handoff, fallback, or escalation;
- a verification step that caught a believable error; and
- stable mechanics that repeated without needing judgment.

The U.S. Army's discussion of
[after-action review](https://www.armyupress.army.mil/Journals/Journal-of-Military-Learning/Journal-of-Military-Learning-Archives/April-2022/Cates-Action-Review/)
informed the comparison between what was intended, what occurred, why it
occurred, and what should change next time. Research on
[outcome bias](https://doi.org/10.1037/0022-3514.54.4.569) is a reminder that a
good result does not, by itself, prove that the decision process was good.

### 4. Turn the candidate into a future-use proposition

Capture normalizes a candidate into one sentence:

> When **this recognizable situation** occurs, use **this method** to produce
> **this result**, within **these boundaries**, and verify it with **this
> evidence**.

This forces the important questions into view: when the method applies, when it
does not, what can vary, what authority it assumes, and how someone will know
the work is actually finished.

The
[ISO process approach](https://www.iso.org/files/live/sites/isoorg/files/archive/pdf/en/iso9001-2015-process-appr.pdf)
informed the input–activity–output–check shape and the idea that controls should
reflect context and risk. Trellis does not claim ISO conformity or turn ordinary
knowledge work into a quality-management system.

### 5. Apply the candidate gates

A candidate must be:

- **Grounded:** traceable to direct owner direction, selected work, or both;
- **Significant:** worth saving and maintaining;
- **Repeatable:** entered by a recognizable future trigger;
- **Applicable:** clear about use, non-use, and variable details;
- **Valid:** faithful to the request or evidence, without unsupported claims;
- **Bounded:** one coherent trigger and outcome; an Action also has one effect,
  approval, success, and recovery boundary;
- **Usable:** followable without hidden conversation context;
- **Distinct:** not already covered by an existing Playbook, Action, or obvious
  local command;
- **Maintainable:** likely to repay its upkeep; and
- **Safe to retain:** free of secrets and private details that do not belong in
  a reusable guide or tool.

The significance, validity, and applicability checks were informed by the
[GAO review of NASA's lessons-learned systems](https://www.gao.gov/products/gao-02-195),
which also illustrates why storing lessons does not ensure that people can find
or apply them. The
[National Academies' review of learning and transfer](https://www.nationalacademies.org/read/9853/chapter/6)
informed the emphasis on applicability across contexts, feedback, and the risk
of carrying a rule into the wrong situation.

Passing the gates does not mean a method is universally true. It means the
candidate is coherent enough to put in front of the user with its uncertainty
visible.

### 6. Keep confidence honest

Capture separates three questions:

- **Method confidence:** Has the way of working transferred beyond its current
  specification or examples?
- **Implementation readiness:** Has this exact Action code been tested?
- **Lifecycle:** Has the owner approved it for active use?

A direct design without evidence from genuinely different real uses, one
completed real-world example, or repeated near-identical cases stays
**Provisional**.
Evidence from genuinely different uses—not copies of the same case—or the
owner's explicit statement that the practice is already established across
them can support **Established** confidence. Capture records that basis without
inventing supporting details. High-consequence work needs representative variation
and important failure boundaries before Established confidence.

This distinction keeps polished prose from masquerading as performance
evidence and keeps a recurring method from masquerading as tested code.

### 7. Find the smallest coherent shape

Capture tests whether a candidate has one trigger family, one recognizable
outcome, and one coherent approval, effect, verification, recovery, and change
boundary. It splits independent jobs and keeps branches together only when
separation would make the promised result incomplete or unsafe.

The
[FAA/NASA study of flight-deck checklists](https://www.faa.gov/sites/faa.gov/files/2022-11/NASA%20Ames%20Rpt%20CR%20177549%20.pdf)
informed the preference for minimum useful cues, coherent phases, interruption
handling, and keeping background explanation outside the point-of-work path.
A Trellis Playbook is broader than a checklist, so judgment and rationale stay
where they change the decision.

### 8. Choose Playbook, Action, both, or nothing

- A **Playbook** keeps contextual judgment: cues, decisions, sequencing,
  exceptions, coordination, and escalation.
- An **Action** performs one mechanically specified job over explicitly scoped
  local files, with observable effects, failure behavior, recovery, and tests.
- A **Playbook and Action** remain separate when a judgment-led workflow uses a
  reusable mechanical operation.
- **Nothing** is the right result for a fact, one-off answer, generic advice,
  unsafe residue, weak idea, duplicate, or candidate not worth maintaining.

The separation between judgment and mechanics is a Trellis design choice. The
model from
[Parasuraman, Sheridan, and Wickens](https://pubmed.ncbi.nlm.nih.gov/11760769/)
is consistent with that stance: it treats information acquisition, analysis,
decision selection, and action implementation as separately allocatable
functions. Guidance such as the
[GSA RPA Playbook](https://www.gsa.gov/cdnstatic/rpa-playbook.pdf) and Google's
[Eliminating Toil](https://sre.google/workbook/eliminating-toil/) also informed
the preference for mature, rules-based candidates with defined triggers,
inputs, outputs, safeguards, observability, and a safe return to human judgment.

Those sources do not prescribe Trellis's local-file-only Action boundary. That
is a deliberate Trellis safety and product choice.

### 9. Put the user at a real decision point

Capture first shows a compact card, then the full artifact and exact file
effects for candidates the user chooses to review. Save, edit, skip, dependency
installation, testing, running, and activation remain separate decisions.

The
[NIST AI RMF 1.0 Appendix C (2023)](https://airc.nist.gov/airmf-resources/airmf/appendices/app-c-ai-risk-management-and-human-ai-interaction/)
informed the emphasis on explicit roles, decision authority, system limits, and
the risk of losing context. Trellis's practical interpretation is that approval
is meaningful only when the user can inspect the proposal, reject it, and see
what will happen.

## What Trellis Synthesized

The cited work informed Trellis; it did not specify or validate Trellis. The
following are product-design choices that should continue to be tested with
real use:

- the direct, reflective, and hybrid input routes;
- the trigger-to-verified-outcome reconstruction model;
- the candidate gates and two-state method confidence;
- the Playbook and Action taxonomy;
- rules for keeping each artifact focused on one coherent job;
- the local-file-only Action safety envelope; and
- the card, proposal, save, test, run, and lifecycle approval sequence.

The methodology is meant to make Trellis inspectable, not to borrow authority
from research conducted for other domains. Reviewer cases, forward tests, user
feedback, and audits of real collections are still necessary to learn where
the model helps, where it creates friction, and what should change.

## The Short Version

Tell Trellis what you want, ask it to look at selected work, or do both. It
turns the material into a bounded future-use proposition, keeps evidence and
intent separate, chooses the smallest fitting form, and shows you the proposal
before anything is saved.
