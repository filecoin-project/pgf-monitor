from fpm.manifest import ExtractSpec
from fpm.reduce import reduce_rows


def _ex(**kw):
    kw.setdefault("column", "v")
    return ExtractSpec(**kw)


def test_single_ok():
    assert reduce_rows([{"v": 3}], _ex(reduce="single")) == 3.0


def test_single_rejects_multiple():
    assert reduce_rows([{"v": 1}, {"v": 2}], _ex(reduce="single")) is None


def test_latest_uses_timestamp():
    rows = [{"v": 1, "t": 100}, {"v": 9, "t": 300}, {"v": 5, "t": 200}]
    assert reduce_rows(rows, _ex(reduce="latest", timestamp_column="t")) == 9.0


def test_avg_min_max():
    rows = [{"v": 2}, {"v": 4}, {"v": 6}]
    assert reduce_rows(rows, _ex(reduce="avg")) == 4.0
    assert reduce_rows(rows, _ex(reduce="min")) == 2.0
    assert reduce_rows(rows, _ex(reduce="max")) == 6.0


def test_empty_or_missing_column_is_none():
    assert reduce_rows([], _ex(reduce="latest", timestamp_column="t")) is None
    assert reduce_rows([{"other": 1}], _ex(reduce="single")) is None
