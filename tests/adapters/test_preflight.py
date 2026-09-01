import httpx
import pytest

from memrank.adapters.preflight import PreflightError, preflight
from tests.fakes import FakeAdapter


def test_preflight_passes_for_reachable_adapter():
    preflight(FakeAdapter(name="ok"))  # no raise


def test_preflight_fails_loud_with_engine_and_url():
    class Broken(FakeAdapter):
        base_url = "http://localhost:9"

        def retrieve(self, *a, **k):
            raise httpx.ConnectError("refused")

    with pytest.raises(PreflightError, match="broken.*http://localhost:9"):
        preflight(Broken(name="broken"))
