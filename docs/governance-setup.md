# Governance setup (applied by a human in GitHub, not by code)

## Teams
- `@filecoin-project/filecoin-propgf-committee`, the oversight committee (CODEOWNERS for registry, allowlist, CODEOWNERS).
- `@filecoin-project/pgf-monitor-maintainers`, repo maintainers (CODEOWNERS for governance logic, gate scripts, and CI workflows).

## Branch protection (default branch `main`)
Require, before merge:
- a CODEOWNERS review,
- status check `validate / static-gate` (green),
- status check `test / test` (green), the classifier's own test suite,
- status check `dry-run / live-dry-run` (green), the merge-blocking live proof.
Do not allow bypass; include administrators.

## Secrets / variables
- Repo secret `OSO_API_KEY`, the filecoin-scoped OSO key (used ONLY by dry-run.yml).
- Repo variable `OSO_ORG_ID`, the filecoin org id.

## Label
- `dry-run-ok`, applied by a committee member after eyeballing the source. Any new push auto-strips it (strip-label.yml), forcing re-review.

## Known residuals
- `source.auth_secret_ref` scoping (design threat 5-3: constrain a manifest to only the submitting team's own secrets) is not yet enforced in code. For the prototype this rests on committee PR review plus the host allowlist, since all current sources are unauthenticated public APIs. Revisit if an authenticated source is ever onboarded.
