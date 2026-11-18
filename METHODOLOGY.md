# Working methods that outlast a session

## Why keep a handbook

Writing, research, planning, and work with customers or teammates teach us both about the task at hand and about how to do similar tasks well. Drafts, notes, plans, and completed results record the work. A handbook keeps the methods that will help with the next task.

For an AI agent entering a new task, a request and a nearby file rarely explain the whole working arrangement: where the current plan is, how much detail a draft needs, which source supports a conclusion, who reviews a change, what else needs checking when something changes, and what would establish that the work is adequate. A handbook answers these recurring questions without anyone reconstructing past conversations.

A handbook's practical value depends on agents finding and applying the relevant material, and on people maintaining that material as the work changes. Writing guidance, having agents find it, and having it applied well are separate achievements.

Trellis provides two skills, the instructions an agent follows to maintain handbooks. Shape Handbook writes and reviews handbooks at a user's request; Learn From Work proposes improvements from experience the user selects. Two of their rules exist because writing guidance secures only the first of those achievements. A handbook's README explains how to use its guidance without Trellis, because those who apply a handbook in ordinary work may not have Trellis. And after Shape Handbook writes to a handbook, its report begins with what remains for the user to do, because guidance that agents cannot find changes nothing about how they work. That step is typically adding a pointer to the handbook in the project's `AGENTS.md`, the instruction file agents read.

## The work and its method

An area's working files hold what people are trying to accomplish, whether an article, a research brief, a team plan, or a response to a customer, with its current content, decisions, and results. The handbook explains how contributors approach, carry out, and review that work. Requirements can sit in either place: a requirement for a particular piece of work stays with that work, and a rule about how such work is done belongs in the handbook.

For example, a team's weekly plan records priorities, dates, and responsibilities. Its handbook can hold a Practice that explains how to agree priorities, a Check that asks whether each commitment has a responsible person and a deadline, and a Playbook that describes the planning meeting; these are the three kinds of guidance described below. The agreed plan and the meeting's actual outcomes stay in the team's working files.

This keeps the handbook focused on reusable methods without making it a second copy of current work. A copy would go stale as the work moved on and leave readers two accounts to reconcile, so a handbook links to the authoritative source and explains how it applies. The distinction holds statement by statement, not file by file: a reusable meeting agenda and the current action list need different homes even when they share a page.

## Three kinds of guidance

A handbook organizes reusable methods as Practices, Checks, and Playbooks. A user does not have to choose among them. One improvement often clarifies a Practice and strengthens a Check together, so a request states the outcome it needs without naming a kind, and each statement goes where its role puts it: a way of working in a Practice, an expectation in a Check, a procedure in a Playbook.

### Practices

A Practice explains how to work in a particular area: who is responsible for what, which distinctions matter, the conventions its writing follows, how to choose a method, and how to read evidence. A Practice belongs in a handbook when it changes a real working decision and is specific enough to apply. Generic advice does not qualify by being true: every reader spends time on it, and no decision changes.

A Practice starts from the area's actual content and existing instructions. The owner (whoever decides policy for the area, often the user) can establish a convention by stating it. A pattern observed in the files is weaker ground: repetition, like the accidental arrangement of files, proves neither that anyone adopted it nor that it helps. A rule inferred from a pattern therefore stays marked as proposed until the owner accepts it, and a handbook keeps what has been adopted apart from what has only been observed or suggested.

Practices are organized around the questions readers bring, with a short way in and each detail stated in one place, so that a reader can start where the task requires, with no set reading order.

### Checks

A Check states an expectation and how to examine it: when it applies, what it requires, how to verify it, and what each outcome means, clearly enough for another reviewer to repeat the examination. Work has to meet its expectations however it was produced, so a Check applies to any work its conditions cover, including work that follows no Playbook.

Many important Checks require judgment: the clarity of writing, the completeness of an argument, the agreement between a report and its notes, the strength of evidence. Automation can support a Check without completing the judgment it requires: a link validator establishes that a target exists, and a reviewer still decides whether the target supports the claim. The same holds for anything that shows only that text exists: reading a Check, completing the headings of a form, or passing such an automated validation is not evidence that the work is adequate.

A Check is applied to work as it is presented. A precise open question can be an adequate contribution to a draft, while a claim presented as settled needs its evidence, and a Check of readiness applies when someone claims the work is ready, not at every earlier stage. The outcomes are pass, fail, unable, and not applicable, each given with its reason. Unable means that missing access, evidence, or clarity prevents a supported conclusion, which is kept apart from failure.

### Playbooks

A Playbook preserves one coherent, repeatable task: when to use it, its intended outcome, the method and the judgment it calls for, the evidence that it is complete, and how to recover or when to stop. It keeps the files the task uses beside those instructions: scripts, longer references, and starters, which are files to copy and fill in. It can call on Practices and Checks, which still apply outside it.

A Playbook is opened at a moment in the work, so its "when to use" names that moment as a contributor would notice it: a subject does not tell anyone that the moment has come. Its judgment sits at the steps where a choice arises, with what prompts the choice and why, because a choice written as a fixed step is followed even where it no longer fits. Branches that start in the same situation and end at the same outcome belong to one Playbook because, kept apart, each would lose the judgment that decides between them.

A written procedure commits later contributors to a way of working, so the choice to preserve one belongs to the user, who asks for it directly or chooses a proposal that clearly contains it; any rule in it that was inferred rather than stated stays marked as proposed until the owner accepts it. An intended procedure can be written before repeated use has proven it.

A request for a template, such as an outline to fill in, produces a Playbook: the outline is kept as a starter beside instructions for when and how to use it, because a form separated from its instructions tends to be completed without judgment. A starter asks for substance: for each of its topics, whoever fills it gives a concrete account, an exact reference to the authoritative source and how it applies, an open question that affects the work, or the reason the topic does not apply.

Scripts are optional and belong to the Playbook whose steps use them. Kept in the Playbook's folder, a script changes together with its instructions, and anyone who depends on it can find out what it does. By default, a script written by Shape Handbook only inspects and reports; it writes only when run with an explicit flag that asks for the change, so that running it merely to look changes nothing. A script can test that the files it touches lie inside the workspace, but that test is code like any other and can be wrong or bypassed, so confining what a script can reach is left to the host, the environment that runs it.

## Local scope and shared practice

Each handbook sits with the area whose work it serves. A handbook at the root of the workspace, the project folder as a whole, can hold Practices shared across it, while a writing, research, or customer-support area keeps its specialized method nearby. Handbooks state their scopes and link to shared rules instead of copying them, which leaves one place to change each rule.

Work that crosses areas may need several handbooks: those that apply to the material being changed and to what depends on it. An area may need more specific guidance, but a handbook in a deeper folder does not thereby overrule one above it. A local rule that departs from a shared one says when the shared rule applies and why it departs, so that a contributor who meets both knows which to follow. Shape Handbook raises an unexplained conflict that would change an important decision instead of letting folder position settle it.

Trellis's skills are allowed less than the work they support: Shape Handbook writes only within the handbook a request concerns, and Learn From Work writes nothing. Agents and people apply a handbook under the authority of their own tasks, meaning what each task is permitted to do. References, written procedures, and scripts do not expand that authority: if guidance could widen what a task may do, writing a document would be a way of granting permission.

## Shaping and learning

The two skills divide the work deliberately. Learn From Work returns each lesson it draws as a proposal: a request the user can edit and give to Shape Handbook. A lesson from one episode is a suggestion about policy, and policy belongs to the owner, so a proposal changes nothing by itself. It waits until the user chooses it by giving that request to Shape Handbook, which then writes the guidance; any rule in it that was inferred from the episode stays marked as proposed until the owner accepts it. The owner's direction can also shape a handbook directly, with no learning exercise before it.

The skills ask questions to return a decision to the person who owns it, not to hand over the work. They read the material a request covers first, then ask about a missing intention, trade-off, or exception when different answers would change the method, and they wait for that answer before treating a rule that depends on it as settled. Diagnosis, organization, writing, and verification remain the agent's; the user need not become a handbook designer. A clear request needs no interview, and a review can report an unresolved choice as a finding.

A correction or an unfinished attempt can reveal a lesson even though it shows no outcome. A successful result does not by itself show which actions produced it, or that every action was necessary or would work elsewhere. A proposal keeps the working method apart from incidental results and carries enough context for the user to act on it without anyone reconstructing the original conversation.

A question asked while learning separates one plausible lesson from another: what prompted a change, which outcome mattered, or where a method would fail to help. The answer is recorded as what the user says now, apart from the evidence examined. When a question goes unanswered, the lesson that depended on it stays tentative: uncertainty is not converted into a claim about the cause. Learning can also conclude that existing guidance already serves, or that the evidence supports no reusable lesson.

## Maintenance and confidence

A handbook improves when work exposes a recurring ambiguity, a missing Check, a method worth repeating, or advice that no longer holds. A change to the work need not change the handbook while the existing method still serves it. A revision removes redundant or superseded material instead of leaving readers to reconcile old accounts with current ones: a handbook describes the arrangement as it now stands, with each rule's present reason and the limits of the evidence behind it.

The test of a handbook is usefulness as well as internal consistency: whether another reader can find what applies, act without inventing missing policy, verify the result, and locate what is unresolved. The cost of maintaining a handbook should stay proportional to the work it improves, and a small handbook that hangs together is a finished result.

Claims about a handbook, and about Trellis itself, go no further than their evidence. Reviewing instructions establishes what was intended; an automated validation establishes selected properties of a document; a script's tests exercise specific program behavior; an independent trial by an agent demonstrates one use. Trellis ships instructions, so what it states is intended behavior; confidence across varied real work requires evidence from that work.
