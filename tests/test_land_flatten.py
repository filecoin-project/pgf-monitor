from fpm.land import flatten_private, flatten_public, to_csv, verdict_rows


def test_flatten_public_has_facts_provenance_narrative_but_not_note_or_approver(sample_bundle):
    row = flatten_public(sample_bundle())
    assert row["team"] == "chainsafe"
    assert row["function_id"] == "forest-uptime"
    assert row["metric"] == "uptime_ratio"
    assert row["sla_outcome"] == "pass"
    assert row["observed_value"] == 0.999
    assert row["threshold_op"] == ">="
    assert row["threshold_value"] == 0.99
    assert row["adjudicated_status"] == "meeting"
    assert row["evidence_bundle_hash"] == "c" * 64
    assert row["manifest_commit_sha"] == "deadbeef"
    assert row["model_id"] == "claude-opus-4-8"
    assert row["narrative"] == "model says: ok, all good"
    assert "adjudication_note" not in row
    assert "approver" not in row


def test_flatten_private_is_public_plus_note_and_approver(sample_bundle):
    row = flatten_private(sample_bundle(note="deferred pending audit", approver="committee-a"))
    assert row["narrative"] == "model says: ok, all good"  # superset
    assert row["adjudication_note"] == "deferred pending audit"
    assert row["approver"] == "committee-a"


def test_evidence_hash_empty_when_absent(sample_bundle):
    b = sample_bundle()
    b.dossier.reading.claim.evidence = None
    assert flatten_public(b)["evidence_bundle_hash"] == ""


def test_verdict_rows_dedupes_by_recommendation_id_last_wins_sorted(sample_bundle):
    first = sample_bundle(rid="rec-1", narrative="old")
    second = sample_bundle(rid="rec-1", narrative="new")  # same id, later adjudication
    other = sample_bundle(rid="rec-0", narrative="other")
    pub, priv = verdict_rows([first, second, other])
    assert [r["recommendation_id"] for r in pub] == ["rec-0", "rec-1"]  # sorted, deduped
    assert next(r for r in pub if r["recommendation_id"] == "rec-1")["narrative"] == "new"
    assert len(priv) == 2


def test_to_csv_round_trips_narrative_with_commas_quotes_newlines(sample_bundle):
    import csv
    import io

    row = flatten_public(sample_bundle(narrative='has, "quotes"\nand a newline'))
    text = to_csv([row])
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert parsed[0]["narrative"] == 'has, "quotes"\nand a newline'
    assert parsed[0]["team"] == "chainsafe"


def test_to_csv_empty_rows_is_empty_string():
    assert to_csv([]) == ""
