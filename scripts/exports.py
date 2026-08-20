"""Generate and publish the two structural exports (see `fpm.exports` for what they are and why).

  uv run python scripts/exports.py write                  # regenerate both CSVs from registry/
  uv run python scripts/exports.py upload --oso-org UUID   # republish both as public static models

`write` is the only way these CSVs should ever change: they are derived from `registry/`, and
`tests/test_exports.py` fails when the committed copies disagree with it. `upload` reuses the same
publish path as the observation and threshold series, including the public read grant.
"""

from __future__ import annotations

import argparse

from fpm.exports import (
    FUNCTIONS_COLUMNS,
    FUNCTIONS_CSV,
    METRICS_COLUMNS,
    METRICS_CSV,
    function_rows,
    metric_rows,
    save_rows,
    unresolved_kernel_ids,
)
from scripts.observations import upload


def write() -> int:
    functions, metrics = function_rows(), metric_rows()
    unresolved = unresolved_kernel_ids(metrics)
    if unresolved:
        # Refuse to publish a mapping that points at a kernel function which does not exist:
        # a consumer joining on kernel_id would silently lose the row.
        for team, function_id in unresolved:
            print(f"ERROR {team}/{function_id}: kernel_id names nothing in the inventory")
        return 1
    save_rows(functions, FUNCTIONS_COLUMNS, FUNCTIONS_CSV)
    save_rows(metrics, METRICS_COLUMNS, METRICS_CSV)
    print(f"{FUNCTIONS_CSV}: {len(functions)} rows")
    print(f"{METRICS_CSV}: {len(metrics)} rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="exports")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("write")
    u = sub.add_parser("upload")
    u.add_argument("--oso-org", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "write":
        return write()
    # Regenerate first: publishing a stale CSV would put the registry and the warehouse out of
    # step, and the whole point of these tables is that they answer for the registry.
    rc = write()
    if rc:
        return rc
    upload(args.oso_org, FUNCTIONS_CSV, "filpgf_kernel_functions")
    upload(args.oso_org, METRICS_CSV, "filpgf_kernel_metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
