# Model-invoked vs user-invoked

Every `SKILL.md` is a skill. The axis that splits them is **invocation**, meaning who can start it:

- **User-invoked**: only the human, by typing its name. Set `disable-model-invocation: true`. The `description` is human-facing: a one-line summary for someone browsing slash commands, without trigger lists. Use it for orchestrations that are expensive, stateful or that the human should decide to start (`reverse-engineer`).
- **Model-invoked**: the model or the human. Omit `disable-model-invocation`. The `description` is model-facing and names the trigger branches ("Use when the user wants..., mentions..., asks for..."), since it decides when the skill fires. Pick this only when the agent should reach the skill on its own or another skill must call it: the description then sits in context in every session.

A user-invoked skill may call model-invoked skills, never another user-invoked one.

## Dependencies between skills

Express a dependency as an explicit instruction to call the Skill tool with the named skill ("Call the Skill tool with `grilling`"), one call per skill. Shared reference material lives inside the skill that owns it. Reference needed only by one skill's workers stays a file in that skill's folder, read by path.

## Workers

Subagents dispatched by a skill are not skills: see [ADR 0002](adr/0002-subagents-in-the-plugin-agents-folder.md).
