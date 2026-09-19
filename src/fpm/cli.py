"""`fpm review <team>` — run the review workflow over a team's merged manifest."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import ApprovalDecision, ReviewRecommendation
from fpm.governance.gitsha import git_manifest_sha
from fpm.pipeline import run_review
from fpm.store import JsonlRecordStore
from fpm.synthesize import FakeReviewSynthesizer, SdkReviewSynthesizer


def run_land_cli(
    store_dir: str,
    org_id: str,
    sink=None,
    public_name: str | None = None,
    private_name: str | None = None,
) -> int:
    from fpm.land import StaticModelSink, land
    from fpm.store import JsonlRecordStore

    bundles = JsonlRecordStore(Path(store_dir)).all_bundles()
    if not bundles:
        print("no bundles to land")
        return 0
    if sink is None:
        import os

        from fpm.oso.static_model import GraphqlStaticModelClient

        client = GraphqlStaticModelClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)
        sink = StaticModelSink(client, org_id)
    kwargs = {}
    if public_name:
        kwargs["public_name"] = public_name
    if private_name:
        kwargs["private_name"] = private_name
    result = land(bundles, sink, **kwargs)
    print(f"landed {len(bundles)} bundles -> public={result['public']} private={result['private']}")
    return 0


def manifest_paths(registry_dir: str, teams: list[str]) -> list[Path]:
    """Named teams, or every adopted manifest. `_`-prefixed files are registry infrastructure
    (_kernel.yaml, _schema.json, _allowlist.txt) and drafts/ is staging, not a commitment."""
    if teams:
        return [Path(registry_dir) / f"{t}.yaml" for t in teams]
    return sorted(p for p in Path(registry_dir).glob("*.yaml") if not p.name.startswith("_"))


def order_by_cost(paths: list[Path]) -> list[Path]:
    """Cheapest manifest first, so a night that runs short collects as many commitments as it can.

    Function count is the cost proxy. A stored duration table would be more accurate and would
    also be one more thing that can go stale; the count tracked the real times closely enough on
    2026-09-17 (1 function/35s, 2/68s, 5/170s) to decide an ordering. Ties break by name so two
    nights' logs are comparable line for line.

    The bias this creates is deliberate but worth naming: slow manifests are disproportionately
    the ones whose ingestion is struggling, so a truncated night preferentially collects the
    healthy ones. That is why every unattempted function still gets a row (`observe.unattempted`)
    -- the skew is visible in the record instead of looking like a quiet night.
    """
    from fpm.manifest import load_manifest

    def cost(path: Path) -> tuple[int, str]:
        try:
            return (len(load_manifest(path).functions), path.name)
        except Exception:
            # Unreadable manifests sort first: they fail in milliseconds and the failure is
            # worth surfacing early rather than after an hour of polling.
            return (0, path.name)

    return sorted(paths, key=cost)


def previous_readings(
    csv_path: Path, as_of: datetime
) -> dict[tuple[str, str, str], tuple[str, float]]:
    """The last value each commitment carried on a day STRICTLY BEFORE `as_of`.

    This is the age guard's comparison point, and the `strictly before` is the whole point. It
    was "the last row per commitment" until 2026-09-19, which silently included a row dated today
    whenever the day already had readings. A second run on such a day then compared today against
    today: `age_growth_violation` saw zero days elapsed, allowed only the 0.5d scheduler-jitter
    budget, and refused any real growth past it -- nulling a correct reading and filing evidence
    for it.

    Caught by a live rehearsal on 2026-09-19: `zondax/rosetta_release_age_days` read 73.48835 at
    the 05:23 nightly and 74.0465 at 19:12. That is +0.558d across 13.8h of real elapsed time, the
    source behaving exactly as it should, and it was thrown away.

    A commitment whose only reading is today's gets NO entry, so the guard does not run for it --
    the same default as a first-ever run, and the right one: there is nothing to compare against.

    Sorted by date rather than trusting file order, because a backfill row can be appended after a
    later nightly one and the last LINE is not the last DAY.
    """
    out: dict[tuple[str, str, str], tuple[str, float]] = {}
    if not csv_path.exists():
        return out

    from fpm import observations as _obs

    today = as_of.date().isoformat()
    for row in sorted(_obs.load_rows(csv_path), key=lambda r: r["observed_at"]):
        if row["observed_value"] in (None, ""):
            continue
        day = row["observed_at"][:10]
        if day >= today:
            continue
        out[(row["team"], row["function_id"], row["metric"])] = (day, float(row["observed_value"]))
    return out


def _host_map(paths: list[Path]) -> dict[tuple[str, str], str]:
    """(team, function_id) -> source host, for grouping failures by where they came from."""
    from urllib.parse import urlparse

    from fpm.manifest import load_manifest

    out: dict[tuple[str, str], str] = {}
    for path in paths:
        try:
            manifest = load_manifest(path)
        except Exception:
            continue  # a manifest that would not load already failed loudly in the run itself
        for fn in manifest.functions:
            out[(manifest.team, fn.function_id)] = urlparse(fn.source.base_url).hostname or "none"
    return out


def run_observe_cli(
    teams: list[str],
    registry_dir: str,
    fixtures: str,
    as_of: datetime,
    method: str,
    csv_path: str,
    live_oso: bool,
    oso_org: str,
    dry_run: bool,
    reprovision: bool = False,
    thresholds_csv: str = "data/thresholds.csv",
    deadline_minutes: float | None = None,
) -> int:
    """Measure every function in every named manifest and append the readings to the CSV.

    Deliberately no synthesizer and no adjudication: this runs unattended. A single team's failure
    is contained the same way a single function's is — recorded, then the batch continues.
    """
    import os
    import time
    from collections import Counter

    from fpm.governance.allowlist import load_allowlist, load_sql_allowlist
    from fpm.guards import capture_dir as guard_capture_dir
    from fpm.observations import append_observations, declared_triples
    from fpm.observe import TRUNCATED_NOTE, observe, thresholds_for
    from fpm.thresholds import append_thresholds

    # A live run takes tens of minutes (47 metrics, each an OSO ingestion run polled to terminal).
    # Every progress line is flushed because stdout is block-buffered whenever it is not a tty —
    # which is always, under GitHub Actions — and an unflushed run shows an empty log for an hour
    # and then everything at once, so a hang is indistinguishable from slow progress.
    def _say(line: str = "") -> None:
        print(line, flush=True)

    oso_client = None
    allowlist: set[str] | None = None
    sql_allowlist: set[str] | None = None
    if live_oso:
        from fpm.oso.graphql_client import GraphqlOsoClient

        oso_client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=oso_org)
        # The committee-maintained allowlists, not ones derived from the manifest being run: a
        # scheduled job must not be able to reach a host, or read a warehouse table, that the
        # committee never approved. The key this client holds is org-scoped and can read private
        # tables, so the table list is the only thing standing between an `oso-sql` metric and
        # applicant identity.
        allowlist = load_allowlist(Path(registry_dir) / "_allowlist.txt")
        sql_allowlist = load_sql_allowlist(Path(registry_dir) / "_sql_allowlist.txt")

    # Cheapest first, so a night that runs short still collects as many commitments as it can.
    # Only when a deadline is in force: without one the run is going to reach every manifest
    # anyway, and alphabetical order keeps the log comparable with every night before this one.
    paths = manifest_paths(registry_dir, teams)
    if deadline_minutes is not None:
        paths = order_by_cost(paths)
    if reprovision and oso_client is not None:
        # Rotating a credential does NOT change the config shape: `config_shape_fingerprint`
        # strips secret values, and OSO's stored config holds only a marker, so there is nothing
        # to compare. Without this, `_ensure_dataset` keeps the dataset carrying the OLD token and
        # every authenticated metric 401s. This is the rotation escape hatch.
        from fpm.manifest import load_manifest
        from fpm.provision import dataset_name

        dropped = 0
        for path in paths:
            try:
                manifest = load_manifest(path)
            except Exception:
                continue
            for fn in manifest.functions:
                existing = oso_client.find_dataset(
                    oso_org, dataset_name(manifest.team, fn.function_id)
                )
                if existing:
                    oso_client.delete_dataset(existing)
                    dropped += 1
        _say(f"reprovision: dropped {dropped} datasets; they rebuild with the current credentials")

    # Last recorded value per commitment, for the age guard in `observe`. Read once here rather
    # than inside the loop: it is the series as it stood BEFORE tonight, which is exactly what
    # today's readings must be checked against -- see `previous_readings` for why "before"
    # had to become literal.
    previous = previous_readings(Path(csv_path), as_of)

    started = time.monotonic()
    _say(f"observing {len(paths)} manifests at {as_of.date().isoformat()}")

    # The wall-clock budget, as a predicate `observe` checks before each metric. A budget rather
    # than a job timeout because the runner's timeout is a SIGKILL: on 2026-09-18 it landed
    # mid-loop and took 20 already-collected readings with it. Stopping ourselves means the
    # remaining steps -- commit, republish, the collection assert -- still run.
    deadline = None if deadline_minutes is None else started + deadline_minutes * 60
    if deadline is not None:
        _say(f"deadline: {deadline_minutes:.0f}m; cheapest manifests first")

    def within_deadline() -> bool:
        return deadline is None or time.monotonic() < deadline

    observations, failed = [], []
    threshold_records: list = []
    for index, path in enumerate(paths, start=1):
        team_started = time.monotonic()
        last = [team_started]

        def progress(obs, _last=last) -> None:
            now = time.monotonic()
            _say(
                f"    {obs.metric[:44]:44} {obs.outcome:14} "
                f"{now - _last[0]:5.1f}s  (+{(now - started) / 60:.0f}m total)"
            )
            _last[0] = now

        _say(f"[{index}/{len(paths)}] {path.stem}")
        try:
            got = observe(
                manifest_path=path,
                fixtures_dir=Path(fixtures),
                as_of=as_of,
                method=method,
                oso_client=oso_client,
                org_id=oso_org,
                allowlist=allowlist,
                poll_sleep=10.0 if live_oso else 0.0,
                on_observation=progress,
                sql_allowlist=sql_allowlist,
                previous=previous,
                should_continue=within_deadline,
            )
        except Exception as exc:
            failed.append(path.stem)
            print(f"    MANIFEST FAILED\t{exc}", file=sys.stderr, flush=True)
            continue
        counts = Counter(o.outcome for o in got)
        _say(
            f"  {path.stem}: {len(got)} metrics  "
            f"pass={counts['pass']} fail={counts['fail']} "
            f"unscored={counts['unscored']} indeterminate={counts['indeterminate']}"
            f"  ({time.monotonic() - team_started:.0f}s)"
        )
        observations.extend(got)
        # Recorded from the manifest that was just measured, so the two tables always carry the
        # same (day, team, function, metric) keys and the render-time join cannot miss.
        team_thresholds = thresholds_for(path, as_of)
        threshold_records.extend(team_thresholds)

        # Persist THIS manifest before starting the next one. Until 2026-09-18 the whole run was
        # appended once at the end, so a process killed mid-loop lost every reading it had taken
        # -- 20 of them that night. Both stores are merge-on-key read-modify-writes, so appending
        # 13 times is idempotent and costs one extra file rewrite per manifest.
        #
        # THRESHOLDS FIRST, READINGS LAST, and the order is load-bearing for the same reason it
        # is on the republish step. These are two separate file writes, so a process killed
        # between them leaves the pair inconsistent; what we get to choose is which direction.
        # A threshold with no reading is a state the system already represents -- thresholds_for
        # emits a row for every function, including ones that produced no value, precisely so an
        # absence is recorded. A reading with no bar is not: the dashboard joins the two on
        # (day, team, function, metric) to derive compliance at render, so a reading that arrives
        # first is a reading nothing can judge. Writing the promise before the measurement makes
        # the only reachable half-state the harmless one.
        if not dry_run:
            append_thresholds(team_thresholds, Path(thresholds_csv))
            append_observations(got, Path(csv_path), declared=declared_triples(registry_dir))

    totals = Counter(o.outcome for o in observations)
    _say(
        f"\n{len(observations)} observations at {as_of.date().isoformat()} "
        f"(pass={totals['pass']} fail={totals['fail']} "
        f"unscored={totals['unscored']} indeterminate={totals['indeterminate']}) "
        f"in {(time.monotonic() - started) / 60:.1f}m"
    )
    # A metric with no value is not a neutral gap: it is a source that has stopped answering, and
    # on 2026-07-15 a third of the registry was already in this state without anyone noticing.
    # Unattempted metrics are excluded deliberately. This block groups blanks by host and hints
    # at a credential, a rate limit or an outage; a metric the run never asked is none of those,
    # and listing it here would turn a short night into a false report of 41 broken endpoints.
    # The truncation summary below counts them instead.
    blank = [
        o for o in observations if o.outcome == "indeterminate" and TRUNCATED_NOTE not in o.note
    ]
    if blank:
        # Grouped by host first, because the shape of the failure names its cause. Blanks spread
        # across many hosts are that many broken sources; blanks concentrated on ONE host are one
        # problem — a rate limit, an outage, or an expired credential for that host. The GitHub
        # paginator bug read as 14 unrelated broken metrics for a month because nothing grouped it.
        hosts = _host_map(paths)
        by_host: dict[str, list] = {}
        for o in blank:
            by_host.setdefault(hosts.get((o.team, o.function_id), "unknown"), []).append(o)
        _say(f"\nno value from {len(blank)} metrics:")
        for host, group in sorted(by_host.items(), key=lambda kv: -len(kv[1])):
            flag = (
                "  <-- one host: suspect a credential, rate limit or outage"
                if len(group) > 2
                else ""
            )
            _say(f"  {host}: {len(group)}{flag}")
            for o in group:
                _say(f"    {o.team}/{o.function_id}\t{o.metric}\t{o.note[:70]}")

    # A refused reading is a different event from a source that went quiet, and it reads as just
    # another `indeterminate` in the list above. Call it out: it means a source returned a number
    # we could prove false, and it is the only night the evidence for that exists.
    refused = [o for o in observations if o.note.startswith("impossible age growth")]
    if refused:
        _say(
            f"\n{len(refused)} reading(s) REFUSED as impossible, evidence in {guard_capture_dir()}:"
        )
        for o in refused:
            _say(f"  {o.team}/{o.function_id}\t{o.metric}\t{o.note[:90]}")

    # A truncated night is a different event from a quiet one, and on 2026-09-18 nothing said so:
    # the run was cancelled, the assert step was skipped, and the gap was noticed a day later by
    # a person. Name it in the log and in the step summary.
    truncated = [o for o in observations if TRUNCATED_NOTE in o.note]
    if truncated:
        teams = sorted({o.team for o in truncated})
        _say(
            f"\nTRUNCATED at the {deadline_minutes:.0f}m deadline: "
            f"{len(truncated)} commitment(s) across {len(teams)} team(s) were not attempted "
            f"({', '.join(teams)}). They are recorded as such, not left as a hole."
        )

    if dry_run:
        _say("\ndry run: nothing written")
    elif observations:
        # Each manifest was already persisted as it finished; this reports the totals.
        _say(f"\n{csv_path}: {len(observations)} rows this run")
        _say(f"{thresholds_csv}: {len(threshold_records)} rows this run")

    if failed:
        print(f"manifests that failed to run: {', '.join(failed)}", file=sys.stderr, flush=True)
        return 1
    if not observations:
        print("no observations produced", file=sys.stderr, flush=True)
        return 1
    return 0


def _interactive_decide(rec: ReviewRecommendation) -> ApprovalDecision:
    ans = input(
        f"Adjudicate {rec.team}/{rec.function_id} [{rec.review_status}] (a/revise/reject/defer): "
    )
    ans = ans.strip().lower()
    if ans in {"a", "approve"}:
        return ApprovalDecision(action="approve", approver="local")
    if ans == "revise":
        status = input("  new status: ").strip()
        return ApprovalDecision(action="revise", approver="local", adjudicated_status=status)  # type: ignore[arg-type]
    if ans == "defer":
        return ApprovalDecision(action="defer", approver="local")
    return ApprovalDecision(action="reject", approver="local")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fpm")
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review", help="review a team's kernel functions")
    review.add_argument("team")
    review.add_argument(
        "--manifest", default="", help="manifest path override (default registry/<team>.yaml)"
    )
    review.add_argument("--fixtures", default="fixtures/responses")
    review.add_argument("--store", default=".fpm_store")
    review.add_argument("--as-of", default="2026-07-01")
    review.add_argument(
        "--dev-auto-approve",
        action="store_true",
        help="TEST ONLY: approve every recommendation without review",
    )
    review.add_argument("--live", action="store_true", help="use the real SDK synthesizer")
    review.add_argument("--live-oso", action="store_true", help="use the live GraphqlOsoClient")
    review.add_argument("--oso-org", default="", help="OSO org id for --live-oso")

    obs = sub.add_parser(
        "observe", help="measure every adopted metric and append the readings to the time series"
    )
    obs.add_argument("teams", nargs="*", help="team names (default: every adopted manifest)")
    obs.add_argument("--registry", default="registry")
    obs.add_argument("--fixtures", default="fixtures/responses")
    obs.add_argument("--as-of", default="", help="observation date (default: today, UTC)")
    obs.add_argument("--method", default="nightly", help="provenance label for the rows written")
    obs.add_argument("--csv", default="data/observations.csv")
    obs.add_argument("--thresholds-csv", default="data/thresholds.csv")
    obs.add_argument("--live-oso", action="store_true", help="fetch for real via the OSO adapter")
    obs.add_argument("--oso-org", default="", help="OSO org id for --live-oso")
    obs.add_argument("--dry-run", action="store_true", help="measure and report, write nothing")
    obs.add_argument(
        "--reprovision",
        action="store_true",
        help="drop and rebuild every OSO dataset first — required after rotating a source "
        "credential, since a new secret does not change the config shape",
    )
    obs.add_argument(
        "--deadline-minutes",
        type=float,
        default=None,
        help="stop measuring after this many minutes and record the rest as unattempted, "
        "instead of letting the runner's own timeout kill the process mid-loop and lose "
        "everything collected so far. Also switches the run to cheapest-manifest-first.",
    )

    report = sub.add_parser("report", help="draft a manifest entry from intent + a source link")
    report.add_argument("team")
    report.add_argument("--link", required=True)
    report.add_argument("--intent", default="")
    report.add_argument("--function-id", default="new-function")
    report.add_argument("--as-of", default="2026-07-01")
    report.add_argument("--out", default="")
    report.add_argument("--live", action="store_true", help="use the real SdkSourceInferrer")

    contract = sub.add_parser(
        "contract", help="render a grant-recipient contract from a team's manifest + facts file"
    )
    contract.add_argument("team")
    contract.add_argument(
        "--facts", default="", help="facts file (default contracts/<team>.facts.yaml)"
    )
    contract.add_argument("--registry", default="registry", help="path to the registry/ dir")
    contract.add_argument("--out", default="", help="write to file (default stdout)")

    land_cmd = sub.add_parser("land", help="land ReviewBundle verdicts into OSO (public + private)")
    land_cmd.add_argument("--store", default=".fpm_store")
    land_cmd.add_argument("--oso-org", required=True)
    land_cmd.add_argument("--public-name", default="", help="public dataset/table name override")
    land_cmd.add_argument("--private-name", default="", help="private dataset/table name override")

    args = parser.parse_args(argv)

    if args.command == "observe":
        as_of = (
            datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
            if args.as_of
            else datetime.now(timezone.utc)
        )
        return run_observe_cli(
            teams=args.teams,
            registry_dir=args.registry,
            fixtures=args.fixtures,
            as_of=as_of,
            method=args.method,
            csv_path=args.csv,
            thresholds_csv=args.thresholds_csv,
            live_oso=args.live_oso,
            oso_org=args.oso_org,
            dry_run=args.dry_run,
            reprovision=args.reprovision,
            deadline_minutes=args.deadline_minutes,
        )

    if args.command == "report":
        from fpm.report.cli_report import run_report_cli

        return run_report_cli(
            team=args.team,
            link=args.link,
            intent=args.intent,
            function_id=args.function_id,
            as_of=datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc),
            out=(args.out or None),
            live=args.live,
        )

    if args.command == "contract":
        from fpm.report.contract import run_contract_cli

        return run_contract_cli(
            team=args.team,
            facts_path=(args.facts or f"contracts/{args.team}.facts.yaml"),
            registry=args.registry,
            out=(args.out or None),
        )

    if args.command == "land":
        return run_land_cli(
            store_dir=args.store,
            org_id=args.oso_org,
            public_name=args.public_name,
            private_name=args.private_name,
        )

    synthesizer = (
        SdkReviewSynthesizer(model_id="claude-opus-4-8", prompt_version="0")
        if args.live
        else FakeReviewSynthesizer()
    )
    if args.dev_auto_approve:
        print(
            "WARNING: --dev-auto-approve bypasses human adjudication. Development only.",
            file=sys.stderr,
        )
        decide = lambda r: ApprovalDecision(action="approve", approver="dev-auto")  # noqa: E731
    else:
        decide = _interactive_decide

    oso_client = None
    allowlist: set[str] | None = None
    sql_allowlist: set[str] | None = None
    if args.live_oso:
        import os
        from urllib.parse import urlparse

        from fpm.governance.allowlist import load_sql_allowlist
        from fpm.manifest import load_manifest
        from fpm.oso.graphql_client import GraphqlOsoClient

        oso_client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=args.oso_org)
        _m = load_manifest(args.manifest or f"registry/{args.team}.yaml")
        allowlist = {
            urlparse(f.source.base_url).hostname for f in _m.functions if f.source.base_url
        }
        allowlist.discard(None)
        # Deliberately NOT derived from the manifest the way the host list above is. Deriving the
        # table list from the file being reviewed would allow whatever that file asks for, which
        # is the entire guard gone; and unlike a host, a table can be a private one this key can
        # already read. So the committee file is the only source, even in an interactive run.
        # Guarded like every other caller: this path is relative, so a review run from
        # outside the repo root (or against a checkout predating the file) would otherwise
        # die with FileNotFoundError before measuring anything. Absent means empty, which
        # refuses every table -- an oso-sql metric reports indeterminate, nothing silently
        # passes, and every other metric in the run is unaffected.
        _sql_path = Path("registry/_sql_allowlist.txt")
        sql_allowlist = load_sql_allowlist(_sql_path) if _sql_path.exists() else set()

    as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    manifest_path = args.manifest or f"registry/{args.team}.yaml"
    manifest_sha = git_manifest_sha(manifest_path)
    bundles = run_review(
        manifest_path=manifest_path,
        fixtures_dir=Path(args.fixtures),
        synthesizer=synthesizer,
        store=JsonlRecordStore(Path(args.store)),
        decide=decide,
        as_of=as_of,
        oso_client=oso_client,
        org_id=args.oso_org,
        allowlist=allowlist,
        poll_sleep=10.0 if args.live_oso else 0.0,
        manifest_commit_sha=manifest_sha,
        sql_allowlist=sql_allowlist,
    )
    for b in bundles:
        rec = b.recommendation
        print(
            f"{rec.function_id}\t{rec.sla_outcome}\t{rec.review_status}\t{b.verdict.adjudicated_status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
