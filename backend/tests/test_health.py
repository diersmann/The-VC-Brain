import re

from fastapi.testclient import TestClient

from app.main import app, create_app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "The VC Brain API"}
    request_id = response.headers.get("x-request-id")
    assert request_id is not None
    assert re.fullmatch(r"[0-9a-f-]{36}", request_id)


def test_unhandled_errors_keep_generic_body_and_request_id() -> None:
    test_app = create_app()

    @test_app.get("/api/v1/_test-error")
    async def _test_error() -> None:
        raise RuntimeError("private founder payload must not escape")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        first = client.get("/api/v1/_test-error", headers={"X-Request-ID": "caller-supplied"})
        second = client.get("/api/v1/_test-error")

    assert first.status_code == 500
    assert first.json() == {"detail": "Internal server error"}
    first_id = first.headers.get("x-request-id")
    second_id = second.headers.get("x-request-id")
    assert first_id is not None and first_id != "caller-supplied"
    assert second_id is not None and second_id != first_id
