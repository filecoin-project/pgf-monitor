---
name: draft-kernel-application
description: Use when preparing a ProPGF KERNEL application for a team ALREADY performing a kernel function without funding — Lily, FilOz's non-Curio work, proving, libp2p, venus and the other unfunded incumbents. Names the kernel function exactly as the schema has it, reuses metrics where a draft exists, and researches and proposes measurable ones where none do. Kernel track only: non-kernel applications (Coordination, RFP) use `draft-application` instead. Triggers on "draft a kernel application for <team>", "prepare an application for Lily", "propose metrics for <function>", "who is doing kernel work without funding", "scope extension", "unfunded kernel work".
---

# Draft an application for work already being done

Most funding applications argue that something *should* exist. These argue that something
**already exists, the network already depends on it, and nobody is paying for it.** That is a
much stronger case, and it is written differently: the evidence is already in the monitoring
repo, so the application is largely a matter of surfacing it.

The deliverable is **the answers, field by field, in the Karma form's own labels and order** —
text a team can paste into `app.filpgf.io` — preceded by reviewer notes flagging every judgment
call. Not a memo, not a pitch.

## Kernel track only — check this first

This skill drafts a **kernel** application: the work maintains a function catalogued in
`registry/_kernel.yaml`, and the application will carry §3 monitored commitments if it lands.

ProPGF funds other things too. A Coordination or RFP application — tooling, research, events,
program support — is a **non-kernel** application, and almost everything below does not apply to
it: no kernel function to name, no §3 monitored commitments, no verification endpoints for a
pipeline to read. Non-kernel grants get **zero** §3 entries; their asks go in requested additions.
Use the general `draft-application` skill for those.

**The test is whether a real `_kernel.yaml` slot fits.** If none does, that is the format telling
you the work is outside the kernel — do not borrow an unrelated slot to force it in. Say the work
is non-kernel and switch skills. Getting this wrong in the applicant's favour is worse than
turning them away: a non-kernel team pushed into the kernel track acquires monitored commitments
it cannot meet and a slot that misattributes someone else's function.

(OSO's own H2 2026 mock is the worked example of the other case: real ProPGF application,
deliberately Category = Coordination, no kernel claim.)

**No clone required.** Every path is a public raw URL:

```
BASE=https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main
```

## Why these applications are different

A cold applicant has to be believed. An incumbent can be checked. Three things exist for these
teams before anyone writes a word:

1. **The function is already catalogued** in `$BASE/registry/_kernel.yaml`, with a `tier` and a
   `value` line saying why the network needs it. That is the case for funding, already written
   and already agreed by the committee.
2. **The metrics are already modelled.** `$BASE/registry/drafts/<team>.yaml` holds proposed
   metrics, sources and thresholds for exactly this function. Field **3.2** of the form — what
   the team will be measured on — normally the hardest field, has a starting point.
3. **There may already be readings.** `$BASE/data/observations.csv` carries real measured history
   for some draft metrics. An application that says "here is the number, measured nightly for
   the last N months" is in a different category from one that promises to measure something.

## The worked example — read it before drafting

**`semantic.mock-karma-application-lily.html`**, an OSO platform memory in the `filecoin` org
(`35c17c26-4aa8-47ba-ba75-be8fe1e3718c`), fetched with `GetAgentUnstructuredMemory`. Built
2026-08-05: a full-fidelity replica of a Karma application page for exactly this case — Lily
(Sentinel chain ETL), already the substrate every open Filecoin dataset sits on, never funded —
applying to Batch 4 for a Nov 2026–Apr 2027 term.

Copy its moves:

- **Facts probed and dated, numbers invented, and the header says which is which.** Repo activity,
  release history, open issue numbers, the network-version state — all real and stamped with the
  date they were checked. Reference number, dollar figures and targets invented. `APP-EXAMPLE-LILY01`
  cannot collide with a real reference.
- **The case is decline, not absence.** It does not argue Lily should exist. It argues the
  maintenance rhythm lapsed — last four releases were dependency bumps, the docs describe a 2023
  snapshot, a two-year-old modelling gap has no funded owner — and names what six months buys.
- **3.2 is a table**: metric · data source · how it's measured · target at end of grant. Every row
  names a specific field in a specific artifact, not "dashboard" or "reports".
- **It proposes the endpoint that makes itself checkable.** Milestone 1 ships a public
  `status.json` so ProPGF can read freshness without asking. An applicant that funds its own
  verifiability is making the reviewer's job easy on purpose.
- **"We would rather be measured on freshness than on commits."** It argues *against* the easy
  proxy: an indexer can be committed to weekly and still be six hours behind head. Say which
  metric would be misleading and why.
- **Overlap is confronted, not hidden.** A risk entry names the other funded work that partly
  replaces it and proposes a boundary at kickoff — "we would rather hand over a table than
  double-fund it".
- **"What we are deliberately not asking for."** Scope discipline, stated, so the ask reads as
  considered rather than maximal.
- **Two fields it proposes the form should have** — see the next section. Carry them into every
  draft.

## Always include the two proposed fields — in a KERNEL application

Every **kernel** application drafted with this skill carries
**`1.7 Kernel function(s) this work maintains`** and **`3.4 Public verification endpoints`**, each
marked `PROPOSED — not in the current form`, with a short reviewer note arguing why it should
exist. In a kernel application they are not optional and not a flourish: they are the program's
standing proposal, and each application is the evidence for it.

**Neither belongs in a non-kernel application.** 1.7 names a kernel function, and a Coordination
or RFP applicant maintains none. 3.4 exists so a monitoring pipeline can read the metrics in §3,
and non-kernel grants have no §3. Adding either to a non-kernel draft would invent a commitment
nobody asked for.

**Mark them clearly.** Neither field exists in the live Karma form. An unmarked extra field looks
like the drafter misread the form; a marked one reads as a deliberate proposal. Set them apart
visually, as the Lily mock does.

**1.7 — the kernel function.** Nothing in the current 22 fields identifies it. `1.5 Category`
offers "Core Infrastructure", which covers most of the inventory, so reviewers infer the function
from the 2.1 prose — and inference is where attribution errors are made. It cannot work at all for
the 18 of 31 functions that share a slot. Downstream, the pipeline needs the tuple
character-for-character and rejects a shared slot with no function named, so a committee decision
recorded in prose has to be re-derived by hand before anything can be measured. The field also
surfaces collisions at submission: Lily's secondary claim is already claimed by three other teams,
which prose would never have shown.

**3.4 — public verification endpoints.** `3.2` asks for a data source and teams answer honestly
with things like "grant records" or "review reports" — private artifacts no pipeline can read. In
one Batch 3 application five of six proposed metrics had no public machine-readable source, found
only in a hand audit weeks after approval. A separate table with an **auth** column forces the
distinction at submission: `auth: none` plus a named field is monitorable, anything else is a
request to fund or unlock a surface. It also gives the applicant somewhere to say "by M1" — a
commitment the grant pays for, which reads very differently from a source that will never be
public. Leave `3.2` as the team's own account of success; `3.4` is the narrower question of what a
machine can check, and separating them means neither has to be watered down.

## Step 1 — pick the team, and know which case it is

Fetch `$BASE/docs/kernel-coverage.md` (auto-generated, so it cannot drift). Every kernel function
whose metrics are **all `draft`** is a candidate: somebody modelled it because it matters, and it
stayed a draft because no grant covers it. Sort by tier — an `irreplaceable` function with no
funded maintainer is the strongest case the program has.

Then look the team up in `$BASE/registry/_grants.yaml`, because the two cases read completely
differently:

- **No grant row → a new applicant.** The whole form, cold. Lily is this case: chain ETL /
  indexing, OSO-authored draft, no counterparty ever identified.
- **Has a grant for a *different* function → a scope extension.** *Lead with this framing.* The
  team is a known, contracted counterparty already delivering, asking to be paid for adjacent
  kernel work it is doing anyway. FilOz is the example: funded for Curio, while also maintaining
  builtin actors, the consensus/validation client, block production and the EVM/EAM actors. Name
  the existing grant and say plainly that this is additional scope, not a re-application.
- **Has a grant naming this function** → not a gap. The coverage matrix should have shown it
  adopted. Stop and report the inconsistency instead of writing an application.

## Step 2 — prove the work is current

A draft can outlive the activity it modelled. Before drafting, check the work is happening now:
recent commits or releases for a GitHub-backed function, a live response for a service. If the
metric has readings, filter `$BASE/data/observations.csv` on the team and metric and quote the
newest `observed_at` and value. **Do not put a team forward on the strength of a manifest alone.**

Then find the real maintainer. Most drafts carry `maintainers: ["@TODO-github-handle"]`, which
means nobody has confirmed a counterparty. Where real handles appear, someone has. Say plainly
if you cannot identify one — an application needs a person, not a repository.

## Step 3 — name the kernel function exactly

This is the field everything downstream keys off, and the one most often got wrong.

`$BASE/registry/_kernel.yaml` is a list of `entries`, each with six fields:

```yaml
- id: fvm-execution-engine
  tier: irreplaceable                                   # irreplaceable | essential | important
  category: Blockchain Core & Physical Storage
  sub_category: VM & Programmability
  function: FVM execution engine (deterministic WASM actor execution)
  value: Shared execution engine that produces gas spent; a divergence here forks
         execution across all clients. Co-maintained by Lotus and Forest.
```

- **`value` is the funding argument, already written and already agreed by the committee.** Do not
  paraphrase it into something weaker. It says why the network cannot do without this.
- **Quote `function` verbatim.** The monitoring pipeline matches `(tier, category, sub_category)`
  character-for-character against this file and rejects anything that does not, so a function
  named loosely in prose has to be re-derived by hand before anything can be measured.
- **The slot usually does NOT identify the work.** Only 13 of 31 functions sit in a slot of their
  own; the other 18 share one with up to four siblings — five functions share
  `essential / Blockchain Core & Physical Storage / Block Production (mining)` alone. Naming the
  slot is not naming the function. Give the `function` string and, where the team maintains more
  than one, order them primary-first and say which is which.
- **Claim only what the team maintains.** The Lily mock explicitly declines a third function in
  its slot that it could plausibly have claimed, and says it would rather see it merged than split
  between two teams. That reads as honest and costs nothing.
- **If nothing fits, say so** and propose an inventory addition as a reviewable PR against
  `_kernel.yaml`. Borrowing an unrelated slot to force a fit is the one outcome to avoid: the slot
  is how the work is later attributed and measured.

## Step 4 — the metrics

Field **3.2** becomes §3 of the grant agreement and then the team's manifest. It is what the team
is eventually held to, so it gets a disproportionate share of the effort.

### If a draft manifest exists

`$BASE/registry/drafts/<team>.yaml` already carries proposed metrics, sources and thresholds for
the function. Start there — but present them **as a proposal for the team to react to**, never as
agreed: they were written by the program, not negotiated, and most drafts carry
`maintainers: ["@TODO-github-handle"]` precisely because no counterparty was ever asked.

### If no metrics exist yet, propose them — this is the real work

Most unfunded kernel functions have never been measured by anyone. Proposing the first metrics is
the substance of the application, and it is a research task before it is a writing task.

1. **Start from `value`, not from the team.** The question is what the network needs this function
   to keep doing, not what the team happens to produce. Lily's `value` is about normalized chain
   data being continuously available, so its metrics are freshness, continuity and
   upgrade-readiness — not commits, not releases, not contributors.

2. **Research what the team actually operates.** Repos, releases, services, endpoints, published
   datasets, dashboards, status pages. Read their docs and their issue tracker; the open issues
   often name the real gap better than any summary. Establish what is *currently true* and date
   it — the mock's facts are stamped "probed 2026-08-05" for this reason.

3. **Find what is already public and machine-readable**, because that is the binding constraint.
   A metric the pipeline can read is JSON, over HTTPS, with **no auth**, reducible to **one
   number**, on a **daily** cadence. Check the host against `$BASE/registry/_allowlist.txt`; a new
   one is fine but needs its own earlier PR.

4. **Reject shapes the pipeline cannot evaluate**, however reasonable they sound. All of these
   reached signed Batch 3 agreements and none is supported:

   | shape | why it fails |
   |---|---|
   | Two-source compare (endpoint vs upstream releases) | needs two fetches and a join |
   | Delta vs a previous period ("no month-over-month decrease") | needs history the fetch does not carry |
   | Date-templated URL (`report_<YYYY-MM-01>.md`) | the URL changes every period |
   | Non-JSON source (markdown, HTML page) | not parseable to a scalar |
   | Tiered threshold keyed to another reading | the bar is not a constant |
   | On-chain contract call | not an HTTP JSON fetch |
   | "Published for context", no threshold | fine as a measurement, but say so deliberately |

   **A commitment the pipeline cannot evaluate is worse than an honest gap** — it reads as
   monitored and silently never fires.

5. **Prefer the outcome over the convenient proxy, and say which proxy you rejected.** The Lily
   mock argues *against* being measured on commits: "an indexer can be committed to weekly and
   still be six hours behind head." Naming the metric that would flatter the team and explaining
   why it is wrong is one of the most credible moves available.

6. **When nothing is readable today, fund the unlock.** Do not invent a proxy to fill the field.
   Name the specific missing surface and put it in a milestone — Lily's M1 ships a public
   `status.json` carrying head lag, newest loaded epoch and missing ranges, which turns five
   would-be-unmeasurable metrics into readable ones. An applicant paying for its own verifiability
   is making the reviewer's job easy on purpose. Group metrics that share one unlock and say so:
   it turns six asks into one.

7. **Do not invent a tight threshold.** Propose a number only where a probe supports it, and say
   what you measured. Otherwise leave it to confirm — a bar nobody agreed to is not a commitment,
   and the registry can carry a metric as measured-but-unscored indefinitely.

8. **Give each metric a source that names a field**, not a system. "Grant records", "review
   reports" and "dashboard inventory" have all been answered in real applications; none is
   readable. The table wants: metric · data source · how it is measured · target at end of grant,
   with the source naming the URL and the field within it.

## Step 5 — draft the form

Field mechanics, the current 22-field list and a working recipe for pulling a real application
live: `$BASE/.claude/skills/draft-application/references/karma-form.md`. The parent skill
`$BASE/.claude/skills/draft-application/SKILL.md` covers each field in depth; this skill only
adds what is specific to an incumbent.

**Mirror a real funded application** rather than working from memory — the curl-and-parse recipe
in `karma-form.md` pulls any application at `https://app.filpgf.io/applications/<APP-REF>`, and
labels change between batches.

Two fields carry the argument:

- **3.2 (the metrics)** — this becomes §3 of the grant agreement and then the team's manifest, so
  it is the field that eventually holds them to something. Start from the draft manifest's
  metrics, and present them **as a proposal for the team to react to**, never as agreed. Where a
  metric already has measured history, say so and give the numbers; that converts a promise into
  a track record.
- **The differentiation field** — an incumbent must say why this is not duplicative of an
  existing grant. For a scope extension, name the funded grant and draw the line between them.

**Open with reviewer notes, outside the form.** The Lily mock puts them in a collapsed block at
the end; either position works as long as they are visibly not part of the application. Put every judgment call in
it with a 🚩, including ones only the recipient can settle: the exact ask, a multiple-choice
field where none of the options fit, a milestone that disagrees with its own verification metric.
A reviewer who can see the open questions can close them in one pass.

## Hard rules

- **Nobody has agreed to any of this.** The draft metrics are OSO-authored, the thresholds were
  written by the program rather than negotiated, and the maintainer handles are mostly
  placeholders. A team that has never been asked has not agreed to anything. Write the
  application *for them to review*, and say so at the top.
- **A speculative application is marked FICTIONAL throughout**, with an invented reference number
  that cannot collide (`APP-EXAMPLE-<SLUG>`), plus a line saying which facts are real and when
  they were checked. Applies to every artifact, every render, every page.
- **Promoting a draft does not create funding**, and adopting one without a grant claims a
  commitment that does not exist. Several of these were *demoted* from adopted on 2026-08-15 for
  exactly that reason. The application is the way in; the registry follows an award, not the
  reverse.
- **Quote adopted coverage, not modelled coverage.** `$BASE/badges.json` carries both:
  `coverage_adopted` is what teams are held to, `coverage_with_drafts` is what is modelled. The
  larger number overstates the program.
- **No money figure comes from this repo, deliberately** — for several grants the committee slate,
  the signed Exhibit B and the maintainers' facts file each carry a different number, and one is
  part-denominated in FIL (see the note atop `_grants.yaml`). Anchor an ask on a defensible basis
  the applicant supplies, such as a monthly rate times the term, so the total reconciles on its
  face. For what a team asked for previously, point at its Karma application.
- **Never invent a metric to fill a field.** If the function cannot be measured from a public
  source today, say so and name the specific unlock, rather than proposing a proxy.

## Failure modes seen before

- **Reading as duplicative of an existing grant.** The most likely rejection for an incumbent.
  Handle it explicitly in the differentiation field rather than hoping nobody asks.
- **Assuming a funded team is funded for everything it does.** The grant row says what is covered,
  the manifest says what is measured, and neither says what else the team maintains.
- **Treating `funded_project_oso_slug` as proof of funding.** It names the payee *if* a grant
  exists. One draft's value is literally `unfunded`.
- **An ask that does not reconcile.** If the total is not obviously derivable from a rate and a
  term, it invites the one objection that has no good answer in a review meeting.

## Hand-off

Deliver the reviewer notes, then the field-by-field answers, then a short list of what the
recipient must confirm before anything is submitted. If several candidates were considered, say
which was chosen and why in two lines — not a survey.
