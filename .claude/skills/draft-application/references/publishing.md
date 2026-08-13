# Optional renders for a drafted application

The raw answers are the deliverable. These are extras — do them on request, not by default. Keep
the answers file as the source of truth and regenerate renders from it.

## 1. Paste-ready markdown (default extra)

One `## <verbatim field label>` heading per field, in form order, value underneath in the field's
shape (arrays as bullets, `3.2` as a markdown table, milestones as sub-blocks). A team copies each
block into the corresponding form input. Put a FICTIONAL banner at the top of speculative drafts,
and keep the rationale for anything unusual **below** the answers so the body stays paste-clean.

## 2. HTML mock of the Karma page

Useful for showing reviewers what a submission looks like in situ, including fields that do not
exist yet. Replicate the real page furniture: top bar, `← Back to Browse Applications`,
`Application for <program>` with the ref chip, the three tabs (Application Details / Milestones /
Comments) with counts, one card per section with a `<label>` + value per field, and a sidebar
carrying the status timeline and an Application info block.

- Self-contained: inline `<style>`, no external fonts, scripts, or images.
- Support light and dark via `@media (prefers-color-scheme: dark)` on CSS custom properties.
- Wide tables go in an `overflow-x: auto` wrapper so the page body never scrolls sideways.
- Mark proposed fields visually (dashed border plus a badge) so nobody mistakes them for live ones.
- Put a mock banner above the page chrome, not inside the content.
- **Verify it renders before claiming it works.** `file:` URLs are blocked in the browser tool:
  ```bash
  cd <dir> && nohup python3 -m http.server 8123 >/dev/null 2>&1 &
  # navigate to http://localhost:8123/<file>.html, screenshot, then: pkill -f "http.server 8123"
  ```
  A 404 on `/favicon.ico` in the console is expected and harmless. Keep screenshots out of the
  repo — write them to the session scratchpad.

## 3. Store it as an OSO org memory

The `filecoin` org keeps mockups as agent unstructured memories, named `semantic.<slug>.<ext>`
with a one-line entry in `semantic.index.md`. Content type is inferred from the extension, so an
HTML mock is `semantic.<slug>.html` (`text/html`).

The MCP tools (`upsertAgentUnstructuredMemory`, `createAgentUnstructuredMemoryUploadUrl`,
`ListAgentUnstructuredMemories`, `GetAgentUnstructuredMemory`) are the normal path. They need a
Bearer token in `.mcp.json`; this repo has none, so fall back to the GraphQL API directly with the
key from `.env`:

```bash
set -a && . ./.env && set +a           # OSO_API_KEY; direnv does not reach subprocesses
q() { curl -s -m 60 -X POST "https://api.oso.xyz/v1/graphql" \
        -H "Authorization: Bearer $OSO_API_KEY" -H "Content-Type: application/json" \
        -A "curl/8" --data "$1"; }
```

**Use curl, not Python `urllib`** — Cloudflare rejects urllib's fingerprint with `403 error code:
1010`, which looks like an auth failure and is not.

Resolve the org id (the `filecoin` org is `35c17c26-4aa8-47ba-ba75-be8fe1e3718c`):

```graphql
query { viewer { id email organizations(first:10){ edges{ node{ id name } } } } }
```

Upload anything non-trivial through staging rather than inline `data`:

1. `mutation($o:ID!){ createAgentUnstructuredMemoryUploadUrl(orgId:$o){ uploadUrl uploadId } }`
2. `curl -X PUT --data-binary @file '<uploadUrl>'` (expires after 1 hour)
3. ```graphql
   mutation($i:UpsertAgentUnstructuredMemoryInput!){
     upsertAgentUnstructuredMemory(input:$i){ success message memory{ id name size contentType updatedAt } }
   }
   ```
   with `input: {orgId, name, uploadId}` — exactly one of `uploadId` or `data`.

Schema gotchas: the upsert payload exposes only `success` / `message` / `memory`, so selecting
`name` at the top level fails validation. `agentUnstructuredMemory(orgId, name)` returns
`{memory, content}`, and `content` comes back **null for large files** — verify a write by
comparing `memory.size` against `wc -c` on the local file instead. `agentUnstructuredMemories`
returns a plain list, not a connection (no `edges`).

Then add one index line under the right heading in `semantic.index.md`
(`* [Title](semantic.<slug>.<ext>) - <one-line description>`) and read it back. The index is
shared and small, so read-modify-write it immediately before the upsert — a concurrent session
converting or renaming memories will otherwise be clobbered, and stale pointers in the index are
how that gets noticed later.
