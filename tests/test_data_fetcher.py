from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_global_snapshot_returns_placeholder_on_failure(monkeypatch):
    import importlib
    import data_fetcher
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
