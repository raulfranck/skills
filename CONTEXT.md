# Skills library

A collection of skills for coding agents, grouped by area and shipped as one Claude Code plugin, `raulfranck-skills`.

## Language

**Area**:
A folder under `skills/` grouping related skills (`engineering`, ...). Every area listed in `plugin.json` ships.
_Avoid_: category, bucket (bucket is reserved for the lifecycle folders `in-progress`, `misc`, `deprecated`)

**Skill**:
A folder holding a `SKILL.md`, loaded by the agent harness as a slash command or an automatic behaviour.

**User-invoked skill**:
A skill only the human can start, by typing its name (`disable-model-invocation: true`).

**Model-invoked skill**:
A skill the agent can also start on its own when its description matches the task.

**Worker**:
A subagent that a skill's orchestrator dispatches for one task, defined in the plugin's `agents/` folder.
_Avoid_: helper, bot

### reverse-engineer

**Run**:
One execution of `reverse-engineer` over a set of repositories, with its own **workspace**.

**Workspace**:
The directory where a run writes everything it produces (`.reveng/<run-id>/`). The analysed repositories stay untouched.

**Lens**:
One analytical question set applied to the code: domain, data, integrations, structure, infra, evolution, flows or risk.
_Avoid_: dimension, perspective

**Task**:
One worker dispatch in a run's plan: an agent, the lenses it applies and its scope. Its ID (`A1`, `B2`, `V1`) prefixes its findings.

**Wave**:
The tasks of a plan that run in parallel. Wave A holds the independent lenses; wave B holds flows and risk.

**Finding**:
A small, checkable claim with a certainty level, an impact and evidence, written as one JSON line.
_Avoid_: insight, observation

**Certainty**:
How strongly a finding is supported: fact, inference, hypothesis or unknown.

**Evidence**:
What supports a finding: a quoted file range, a commit, a search, or a script artifact.

**Verdict**:
The independent verifier's judgement on one finding: confirmed, downgraded, refuted, relocated or unverifiable.

**Declared model**:
What documentation, names and folder structure claim about a system. The analysts test it against the code (Reflexion) and record convergences, divergences and absences.

**Hotspot**:
A file that changes often and is complex: where change cost and risk concentrate.

## Relationships

- The plugin ships every listed **Area**; an **Area** holds many **Skills**, and a **Skill** may dispatch **Workers**
- A **Run** has one **Workspace** and one plan of **Tasks** grouped in **Waves**
- A **Task** applies one or more **Lenses** to a scope and writes **Findings**
- A **Finding** carries one **Certainty** and receives at most one **Verdict**
