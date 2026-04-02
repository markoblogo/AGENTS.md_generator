### **Manifest: Agentsgen Philosophy**

**Agentsgen exists because “context files” are easy to get wrong.**

Recent research suggests that auto-generated context files can _hurt_ agent performance while increasing cost. We take that seriously.

### **Principles**

1. **No text for the sake of text.**

   If a file doesn’t reduce mistakes or speed up decisions, it doesn’t belong in the “always loaded” context.

2. **Minimal, maintained, verifiable artifacts.**

   We prefer a few small, stable docs that stay true over time:

- AGENTS.md / RUNBOOK.md for workflow contracts

- docs/ai/* + llms.txt for LLM-ready repo context

- machine-readable outputs when possible (JSON, manifests)

- explicit bridge artifacts when repo context must meet portable human context (`docs/ai/id-context.json`)

3. **Instrumented truth beats prose.**

   The source of truth is not “a nice description.”

   The source of truth is what can be validated:

- agentsgen check (drift / missing files / broken markers)

- agentsgen status (what is managed, what is generated, what is drifting)

- agentsgen pack --check (LLMO pack consistency)

4. **Progressive disclosure over a monolith.**

   One giant AGENTS.md doesn’t scale.

   We aim for layered context: global rules stay small; deeper docs are pulled when relevant.

5. **Safe-by-default, always.**

   We only update inside explicit markers.

   If markers are missing, we write *.generated.* instead of touching your hand-written docs.

### **What this is not**

- Not “/init and forget”.

- Not a documentation generator for humans.

- Not SEO magic.

   It’s a conservative toolchain for keeping agent-facing repo context **correct** and **cheap**.

### **Two papers worth reading**

- **Do Context Files Help?** (ETH Zurich) — auto-generated context can reduce resolve rate and increase cost.

- **Codified Context** — why scalable agent work needs layered, evolving context rather than a single file.

(Links are in the README references section.)
