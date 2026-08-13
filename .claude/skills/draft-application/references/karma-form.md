# The Karma application form — field set and shapes

Data reference for `draft-application`. **Refresh it before drafting** — labels and numbering
change between batches. Last read 2026-08-05 from Batch 3 application `APP-9PTCWEQL-HVKGV8`.

## Fetch a real application

The page at `https://app.filpgf.io/applications/<APP-REF>` is a Next.js RSC app, but the whole
application object ships in the served HTML. No browser and no auth needed:

```bash
curl -s "https://app.filpgf.io/applications/APP-9PTCWEQL-HVKGV8" -o app.html
```

```python
import re, json
h = open("app.html").read()
chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)</script>', h, flags=re.S)
payload = "".join(json.loads(c) for c in chunks)          # RSC stream, concatenated
start = payload.index("{", payload.index('"application":'))
app, _ = json.JSONDecoder().raw_decode(payload[start:])   # full application object
print(list(app["applicationData"]))                       # the field labels, in order
```

`app` also carries `status`, `statusHistory`, `referenceNumber`, `approvedAmount`,
`aiEvaluation`, `milestoneStatuses`, `projectUID`, `createdAt` / `updatedAt`.

Stripping tags for visible text works too, but loses `2.4 Milestones & Budget` — it renders in a
separate tab.

## Field set (Batch 3, 22 fields, in order)

| Label (verbatim) | Shape |
|---|---|
| `1.1 Project Name` | string |
| `Karma Profile` | string (project UID hash) — unnumbered |
| `1.2 Project Github` | URL |
| `1.3 Project Website` | URL |
| `1.4 Team Lead/Point of Contact` | string: name, role, Slack/Telegram handle |
| `1.5 Category` | **array** — e.g. `["Core Infrastructure"]` |
| `Contributing to Core Infrastructure?` | prose, 2–4 sentences — unnumbered, conditional on 1.5 |
| `1.6 Open Source Status` | string — e.g. `"Fully Open Source"` |
| `2.1 Project Summary` | prose, several paragraphs; the main narrative field |
| `2.2  Who does this work support?` | **array** — note the **two spaces** after `2.2` |
| `2.3 Total Funding Requested (USD)` | string, e.g. `"USD $240,000 (over a 6-month term, Oct 2026 – Mar 2027)"` |
| `2.4 Milestones & Budget` | **array of objects** — see below |
| `Objective 1` / `Objective 2` / `Objective 3` | string: `"Direct"` / `"Indirect"` — three separate fields |
| `3.1 Impact pathway` | prose, conventionally `Output:` / `Outcome:` / `Impact:` bullet blocks |
| `3.2 Verification metrics` | **markdown table**: Metric \| Data source \| How it's measured \| Target (end of grant) |
| `3.3 References` | markdown bullets |
| `4.4 Core Team` | prose or bullets — numbering jumps from 3.3 |
| `4.5 Has your team received a ProPGF grant or funding from PLFIF before?` | **array** — `["Yes"]` / `["No"]` |
| `5.1 Key risks & dependencies` | markdown bullets, risk + mitigation per bullet |
| `Anything else you want to share that we didn't ask?` | free prose — unnumbered; teams use it for funding history and prior-batch allocation |

### `2.4 Milestones & Budget` object

```yaml
title: "Milestone 1 — <theme> (<months>) · $<amount>"
dueDate: "2026-12-31"              # ISO; must fall inside the stated term
fundingRequested: "USD $120,000"
completionCriteria: |              # newline-separated bullets, each with its $ share
  - <workstream>, 3 months of service — $45k
  - ...
milestoneUID: "0x…"                # assigned by Karma; omit when drafting
description: "$2d"                 # unresolved RSC ref when read back — ignore it
```

Line items must sum to `fundingRequested`; milestones must sum to `2.3`.

## Observed values

- **1.5 Category**: `Core Infrastructure` (Batch 3 also ran an RFP-response track)
- **2.2 audiences**: `Pods`, `Storage Providers`, `Application Builders`,
  `Network Infrastructure`, `Application Users`, `Onramps`
- **1.6**: `Fully Open Source`
- **Objectives 1–3**: `Direct` / `Indirect` — the network-strategy objectives; infrastructure and
  coordination work is normally `Indirect` across all three

## Status lifecycle

`statusHistory` cycles `Pending → Under Review → Revision Requested → Under Review → …` →
`Approved` ("Funded & ready to build"). `approvedAmount` stays empty until approval, and can
differ from 2.3 — reviewer notes in the history often ask for a specific budget revision, so
**never take the committed figure from the application**. Exhibit B of the signed agreement is
the only authority.
