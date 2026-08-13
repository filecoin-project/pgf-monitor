---
name: draft-application
description: Use when drafting a ProPGF funding application BEFORE any award — produces the raw field-by-field answers for the Karma form (app.filpgf.io), grounded in probed facts and pinned to a Kernel function. Triggers on "draft an application", "mock application", "what would <team>'s application look like", "fill in the Karma form", "pre-populate an application". Once an award exists and metrics must be committed to, use `reconcile-metrics`.
---

# Draft a ProPGF application

The deliverable is **the answers, one per Karma field**, in the form's own labels and order —
text a team pastes into `app.filpgf.io`. Not a memo, not a pitch, not an HTML page. Renders are
an optional last step.

Two audiences, same output: a real team drafting its own submission, or ProPGF drafting a
speculative one to show what a good application looks like. The second must be marked FICTIONAL
everywhere, including the reference number.

## New here? Read this first

`README.md` explains the program and the kernel in five minutes. **ProPGF** funds teams that
maintain the **kernel** — the functions the Filecoin network cannot operate without, catalogued in
`registry/_kernel.yaml`. Applications are submitted through **Karma** (`app.filpgf.io`) and get a
reference like `APP-XXXXXXXX-XXXXXX`. Field **3.2** is where an applicant proposes the metrics
they'll be held to; those become §3 of the grant agreement's Appendix 1 and then a **manifest**
(`registry/<team>.yaml`) if the grant lands — which is why 3.2 gets a disproportionate share of
this skill.

Prerequisites: `uv sync` once, and network access for the probes in step 3. No credentials needed.

## Ground truth, in priority order

1. **What the team tells you** — scope, budget, term, people, what they will commit to. Never
   invent any of it. Missing means `TODO — <who> to supply`, not a plausible guess.
2. **The live field set** — `references/karma-form.md`, refreshed from a real application before
   you write (labels and numbering shift between batches).
3. **`registry/_kernel.yaml`** — the function being claimed, character-for-character.
4. **The project's own artifacts, probed today** — repo, releases, changelog, docs, endpoints.
5. **A neighbouring team's application** for register and length. `registry/*.yaml` headers cite
   app refs; `contracts/*.facts.yaml` (gitignored) carry §3.2 metrics verbatim.

## Workflow

1. **Pin the program and term.** Batch, month of submission, term length, milestone count and due
   dates. A 6-month term is normally two milestones. Get this wrong and every date downstream is
   wrong.

2. **Refresh the field set.** Fetch a real application and read the labels off it — see
   `references/karma-form.md` for the curl recipe and the current 22-field list. Labels have
   quirks worth preserving (`2.2  Who does this work support?` has two spaces; numbering jumps
   from 3.3 to 4.4; two fields are unnumbered). Never retype labels from memory.

3. **Probe before writing.** Every activity claim in 2.1 and 5.1 must come from something you
   read today, with the date recorded:
   ```bash
   curl -s "https://api.github.com/repos/<org>/<repo>" | python3 -m json.tool | head -40
   curl -s "https://api.github.com/repos/<org>/<repo>/releases?per_page=6"
   curl -s "https://api.github.com/repos/<org>/<repo>/issues?state=open&sort=created&direction=desc&per_page=30"
   ```
   Read the changelog too — a run of dependency-bump releases is the difference between "actively
   developed" and "kept compiling", and that distinction is usually the whole argument. Parse JSON
   with a parser: `grep -c` on single-line JSON counts lines, not items, and silently returns 1.

4. **Choose the Kernel function.** Copy tier / category / sub_category / function from
   `registry/_kernel.yaml` verbatim. Then check who already claims it:
   ```bash
   grep -rn "kernel_function" registry/*.yaml | sort -t: -k3
   ```
   A slot holding several functions (Essential · Coordination & Incentives · Network data &
   monitoring holds three) means naming the slot does not identify the work — name the string. A
   function four teams already report against is a crowding signal: say so in the draft rather
   than quietly adding a fifth claim. If nothing in the inventory fits, that is the format telling
   you the work is outside the Kernel; say that instead of borrowing a slot.

5. **Write the scope and budget fields (2.1–2.4).** 2.1 is three or four paragraphs: what the
   thing is, what has lapsed or is needed (with the probed evidence), then a numbered list of what
   this grant buys. Then check the arithmetic — per-milestone line items must sum to that
   milestone's `fundingRequested`, and the milestones must sum to 2.3. Verify every date exists
   (February 30 and September 31 both reached signature in batch 3).

6. **Write 3.2 verification metrics.** This is the field the rest of the program runs on, and the
   one teams get wrong. Four columns: Metric | Data source | How it's measured | Target.
   - A source is only usable if it is **public, unauthenticated, and machine-readable today** —
     or the application states the milestone by which it will be. "Our grant records", "review
     reports", "the internal dashboard" are not sources. In one batch-3 application five of six
     proposed metrics had no readable source, discovered weeks after approval.
   - Where several metrics need the same missing endpoint, say so. One unlock buying four metrics
     is a much better ask than four separate ones.
   - Distinguish a **continuous series** from a **delivery gate**. "PR merged", "issue closed",
     "inventory complete" reads as breaching every month until it lands, then passes forever.
     Either frame it as a milestone or flag the shape explicitly.
   - Do not substitute a proxy for the commitment. Release cadence is not version readiness (a
     release can be tagged on time and not carry the bundle); commit recency is not pipeline
     freshness. If the honest metric needs a field that does not exist, ask for the field.
   - Targets are the applicant's commitment. Derive from a probe and say so, or mark
     "to confirm". Never invent a tight threshold to look rigorous.

7. **Write 4.x and 5.1 from evidence.** Core team as roles and FTE unless the team supplies names.
   Risks should include the ones a reviewer would raise anyway: upstream release cadence,
   key-person concentration, cost drift, and any **overlap with other ProPGF-funded work** — check
   `registry/` and recent applications for someone already funded to build the same thing, and
   propose the boundary rather than waiting to be asked.

8. **Optional renders.** The raw answers are the deliverable; these are extras, on request:
   a paste-ready markdown file, an HTML mock of the Karma page, or an OSO org memory. See
   `references/publishing.md`.

## Hard rules

- **Never fabricate a person.** No invented names, handles, or quoted commitments — roles and
  `@<handle>` placeholders instead. This holds double for speculative drafts, which put words in
  a real org's mouth.
- **Never invent money.** No figure without the team's number behind it, or a `TODO`.
- **Mark speculative drafts FICTIONAL** at the top of every artifact, with an invented ref number
  that cannot collide (`APP-EXAMPLE-<SLUG>`), and a line saying which facts are real and when
  they were probed.
- **Do not write a metric you have not verified** is readable, or state the milestone that makes
  it readable.
- Keep the answers in the form's own field labels and order. A reviewer diffing against the live
  application should see the same structure.

## Failure modes

- **Labels from memory.** They drift per batch, and a mislabelled answer lands in the wrong field.
- **Prose where a shape is expected.** 1.5 / 2.2 / 4.5 are multi-selects, 3.2 is a markdown table,
  2.4 is a list of milestone objects. See `references/karma-form.md`.
- **A milestone list that doesn't sum**, or a due date outside the stated term.
- **Kernel slot named but not the function** — ambiguous in the shared slots, and the monitoring
  pipeline rejects it downstream.
- **Ecosystem-benefit prose in place of an answer.** Every field is a question; answer it.
- **Padding 3.2 to six rows.** Four defensible metrics beat six with two unmeasurable ones.

## Optional: the two proposed fields

When the point of the draft is to show what intake *should* collect, add these and mark them
clearly as **not in the current form**:

- `1.7 Kernel function(s) this work maintains` — multi-select from `registry/_kernel.yaml`,
  ordered, primary first, storing the verbatim string plus tier/category/sub-category, with a
  "propose an inventory addition" escape hatch. Nothing in the current 22 fields identifies the
  function; `1.5 Category` offers "Core Infrastructure", which covers most of the inventory.
- `3.4 Public verification endpoints` — repeating row: URL or dataset, auth requirement, field to
  read, refresh cadence, available now or by which milestone. The auth column is the point: it
  separates monitorable from aspirational at submission time instead of during a hand audit.

## Hand-off

`draft-application` produces the answers → `reconcile-metrics` decides which of the proposed
metrics are measurable and become §3 of the grant agreement → `author-manifest` turns the agreed
rows into `registry/<team>.yaml` SLAs, which `reconcile-metrics` then keeps in step with the signed
document. Writing 3.2 with the appendix's four-line shape in mind (metric, source, threshold,
statement) makes the next two steps mechanical instead of a re-derivation.
