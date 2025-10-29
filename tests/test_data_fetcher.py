from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_global_snapshot_returns_placeholder_on_failure(monkeypatch):
    import importlib
    from app.services import data_fetcher
    import requests

    data_fetcher = importlib.reload(data_fetcher)

    # ensure no persistent cache exists
    if data_fetcher.GLOBAL_SNAPSHOT_CACHE_FILE.exists():
        data_fetcher.GLOBAL_SNAPSHOT_CACHE_FILE.unlink()

    def _fail_request(url, params):
        raise requests.exceptions.HTTPError("forced failure")

    monkeypatch.setattr(data_fetcher, "_request_with_retry", _fail_request)

    snapshot = data_fetcher.get_global_market_snapshot()
    assert len(snapshot) == len(data_fetcher._GLOBAL_SYMBOLS)
    assert all(item["price"] is None for item in snapshot)
    assert data_fetcher.get_last_data_error("global_market_snapshot")


def test_sector_performance_fallback(monkeypatch):
    import importlib
    from app.services import data_fetcher

    data_fetcher = importlib.reload(data_fetcher)

    monkeypatch.setattr(
        data_fetcher.stock, "get_nearest_business_day_in_a_week", lambda: "20240614"
    )

    def _snapshot(sector_name, *_args, **_kwargs):
        return {
            "섹터": sector_name,
            "현재가": 100.0,
            "전일대비": 1.0,
            "등락률(%)": 1.0,
        }

    monkeypatch.setattr(data_fetcher, "_load_sector_snapshot", _snapshot)
    success_df = data_fetcher.get_sector_performance()
    assert not success_df.empty

    def _raise_snapshot(*_args, **_kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(data_fetcher, "_load_sector_snapshot", _raise_snapshot)

    fallback_df = data_fetcher.get_sector_performance.__wrapped__(top_n=5)
    assert not fallback_df.empty
    assert data_fetcher.get_last_data_error("sector_performance::5")


def test_search_news_handles_exception(monkeypatch):
    import importlib
    from app.services import data_fetcher

    data_fetcher = importlib.reload(data_fetcher)

    class _FailingDDGS:
        def __enter__(self):
            raise RuntimeError("ddgs init failed")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(data_fetcher, "DDGS", lambda: _FailingDDGS())

    results = data_fetcher.search_news("삼성전자")
    assert results == []
