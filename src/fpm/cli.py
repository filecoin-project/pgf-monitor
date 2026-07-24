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
    if args.live_oso:
        import os
        from urllib.parse import urlparse

        from fpm.manifest import load_manifest
        from fpm.oso.graphql_client import GraphqlOsoClient

        oso_client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=args.oso_org)
        _m = load_manifest(args.manifest or f"registry/{args.team}.yaml")
        allowlist = {
            urlparse(f.source.base_url).hostname for f in _m.functions if f.source.base_url
        }
        allowlist.discard(None)

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
    )
    for b in bundles:
        rec = b.recommendation
        print(
            f"{rec.function_id}\t{rec.sla_outcome}\t{rec.review_status}\t{b.verdict.adjudicated_status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
