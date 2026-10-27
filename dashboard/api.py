"""Thin client for the verifyKYB FastAPI backend (with graceful error handling)."""
from __future__ import annotations

import os

import requests

BASE_URL = os.environ.get("VERIFYKYB_API_BASE", "http://127.0.0.1:8000")

# (connect, read). Registry/crawl calls can legitimately take a while.
_SLOW = (5, 175)
_FAST = (5, 30)


class ApiError(RuntimeError):
    """A user-friendly backend/network error."""


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _call(method: str, path: str, *, timeout, **kw) -> requests.Response:
    try:
        return requests.request(method, _url(path), timeout=timeout, **kw)
    except requests.exceptions.ConnectTimeout:
        raise ApiError(f"Could not connect to the backend at {BASE_URL} in time.")
    except requests.exceptions.ConnectionError:
        raise ApiError(f"Backend not reachable at {BASE_URL}. Is uvicorn running?")
    except requests.exceptions.ReadTimeout:
        raise ApiError(
            "The backend took too long. For US registry lookups, pick a state "
            "(a nationwide search hits all 51 registries and is very slow), or "
            "set REGISTRY_PROVIDER=mock for instant testing."
        )
    except requests.exceptions.RequestException as exc:
        raise ApiError(f"Request failed: {exc}")


def health() -> dict:
    return _call("GET", "/health", timeout=_FAST).json()


def create_case(payload: dict) -> requests.Response:
    return _call("POST", "/kyb/cases", json=payload, timeout=_SLOW)


def get_case(case_id: str) -> requests.Response:
    return _call("GET", f"/kyb/cases/{case_id}", timeout=_FAST)


def list_cases(status: str | None = None, rating: str | None = None,
               decision: str | None = None, limit: int = 50) -> dict:
    params = {k: v for k, v in
              {"status": status, "rating": rating, "decision": decision, "limit": limit}.items()
              if v}
    return _call("GET", "/kyb/cases", params=params, timeout=_FAST).json()


def run_footprint(case_id: str) -> requests.Response:
    return _call("POST", f"/kyb/cases/{case_id}/footprint", timeout=_SLOW)


def get_footprint(case_id: str) -> requests.Response:
    return _call("GET", f"/kyb/cases/{case_id}/footprint", timeout=_FAST)


def post_action(case_id: str, action: str, notes: str, actor: str) -> requests.Response:
    return _call("POST", f"/kyb/cases/{case_id}/actions",
                 json={"action": action, "notes": notes, "actor": actor}, timeout=_FAST)


def recompute_risk(case_id: str) -> requests.Response:
    return _call("POST", f"/kyb/cases/{case_id}/risk", timeout=_FAST)


def get_memory(case_id: str) -> dict:
    return _call("GET", f"/kyb/cases/{case_id}/memory", timeout=_FAST).json()


def explain_case(case_id: str) -> requests.Response:
    return _call("POST", f"/kyb/cases/{case_id}/explain", timeout=_SLOW)


def get_report(case_id: str) -> requests.Response:
    return _call("GET", f"/kyb/cases/{case_id}/report", timeout=_FAST)
