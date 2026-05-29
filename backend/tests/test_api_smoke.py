"""
Smoke do bloco 6: a app FastAPI sobe sem erro e os routers estão montados.

Não usa DB — só verifica que `/openapi.json` lista as rotas esperadas.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_lists_expected_routes() -> None:
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    paths = set(spec["paths"].keys())
    expected = {
        "/tasks",
        "/tasks/{task_id}",
        "/tasks/{task_id}/prompts",
        "/tasks/{task_id}/testcases",
        "/tasks/{task_id}/rubric",
        "/tasks/{task_id}/prompts/{version_number}",
        "/tasks/{task_id}/prompts/diff",
        "/model-configs",
        "/runs",
        "/runs/recent",
        "/runs/{run_id}",
        "/runs/{run_id}/status",
        "/runs/{run_id}/results",
        "/scorecards/{run_id}",
        "/tasks/{task_id}/leaderboard",
        "/compare",
        "/export/{run_id}",
        "/health",
    }
    missing = expected - paths
    assert not missing, f"rotas faltando no openapi: {missing}"
