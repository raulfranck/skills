# Lens: evolution

**Question**: how did the system get here, where does change concentrate, and who knows what?

**Techniques**: behavioural code analysis (Tornhill): hotspots as change frequency times complexity, change coupling, code age, knowledge maps and truck factor; mining software repositories; software archaeology, reading commits, tags, pull requests and ADRs for the why; Learn from the Past (Object-Oriented Reengineering Patterns).

**Start from**: `recon/<repo>/git-metrics.md` and `.json`; the log of each hotspot file; tags; large commits; ADRs and the changelog.

## Procedure

1. **Data quality.** History depth (shallow?), squash merges, bots, mass reformatting commits, renames: what the metrics can and cannot say. Done when the reliability of the metrics is recorded.
2. **Hotspots.** For the top 10, find why the file changes so often (`git log --format='%h %ad %s' --date=short -n 30 -- <file>`) and why it is complex (read it briefly). Classify it: healthy core under active development, accumulated debt, a configuration or registry file, or noise. Done when each has an explanation grounded in commits or code.
3. **Change coupling.** Interpret the top pairs, cross-module ones first. Each is either a hidden dependency (a shared concept, copied code, a contract kept in sync by hand) or an expected one (a test and its subject).
4. **Knowledge.** Modules with a single main author (over 70% of changes) or a truck factor of 1, and areas whose main authors have gone quiet. Report the distribution of knowledge; judgements about people stay out.
5. **Timeline.** The phases of the project, from monthly activity, tags and large commits: creation, growth, rewrites, migrations, freezes. The ADRs and commits that explain each turning point.
6. **Trends.** The areas heating up and the areas cooling down.

## Kinds

`history-quality`, `hotspot`, `temporal-coupling`, `knowledge-risk`, `milestone`, `trend`, `note`

## Narrative outline

Reliability of the history · Hotspots (table: file, why it churns, class) · Hidden coupling · Knowledge distribution · Timeline and turning points · Open questions
