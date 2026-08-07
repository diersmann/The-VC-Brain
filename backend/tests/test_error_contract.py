import re

from fastapi import HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.main import create_app


def test_http_errors_use_v1_envelope_and_retain_detail() -> None:
    test_app = create_app()

    @test_app.get("/api/v1/_test-errors/{status_code}")
    async def _test_error(status_code: int) -> None:
        details = {
            404: "Record detail remains available to legacy clients",
            409: {"state": "already_exists"},
            503: "Queue detail remains available to legacy clients",
        }
        raise HTTPException(status_code=status_code, detail=details[status_code])

    with TestClient(test_app) as client:
        for status_code, code, retryable, detail in (
            (404, "not_found", False, "Record detail remains available to legacy clients"),
            (409, "conflict", False, {"state": "already_exists"}),
            (503, "service_unavailable", True, "Queue detail remains available to legacy clients"),
        ):
            response = client.get(f"/api/v1/_test-errors/{status_code}")
            payload = response.json()

            assert response.status_code == status_code
            assert payload["version"] == "v1"
            expected_detail = (
                detail if status_code < 500 else "The service is temporarily unavailable."
            )
            assert payload["detail"] == expected_detail
            assert payload["error"]["version"] == "v1"
            assert payload["error"]["code"] == code
            assert payload["error"]["retryable"] is retryable
            assert re.fullmatch(r"[0-9a-f-]{36}", payload["error"]["request_id"])


def test_request_validation_uses_safe_message_and_preserves_validation_detail() -> None:
    test_app = create_app()

    @test_app.get("/api/v1/_test-validation")
    async def _test_validation(limit: int = Query(..., ge=1)) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(test_app) as client:
        response = client.get("/api/v1/_test-validation?limit=not-an-integer")

    payload = response.json()
    assert response.status_code == 422
    assert payload["version"] == "v1"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "The request could not be validated."
    assert payload["error"]["retryable"] is False
    assert payload["detail"][0]["type"] == "int_parsing"
    assert payload["detail"][0]["msg"] == "The request field is invalid."
    assert "input" not in payload["detail"][0]
    assert "not-an-integer" not in response.text


def test_validation_messages_do_not_echo_custom_exception_text() -> None:
    test_app = create_app()

    @test_app.get("/api/v1/_test-secret-validation")
    async def _test_secret_validation() -> None:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", "token"),
                    "type": "value_error",
                    "msg": "Value error, private token must not escape",
                    "input": "private-token",
                }
            ]
        )

    with TestClient(test_app) as client:
        response = client.get("/api/v1/_test-secret-validation")

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "The request field is invalid."
    assert "private token" not in response.text
    assert "private-token" not in response.text


def test_method_not_allowed_uses_v1_envelope_and_preserves_allow_header() -> None:
    test_app = create_app()

    @test_app.post("/api/v1/_test-method")
    async def _test_method() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(test_app) as client:
        response = client.get("/api/v1/_test-method")

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert response.json()["version"] == "v1"
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_unhandled_errors_remain_generic_inside_v1_envelope() -> None:
    test_app = create_app()

    @test_app.get("/api/v1/_test-error")
    async def _test_error() -> None:
        raise RuntimeError("private founder payload must not escape")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_test-error")

    payload = response.json()
    assert response.status_code == 500
    assert payload["version"] == "v1"
    assert payload["detail"] == "Internal server error"
    assert payload["error"]["code"] == "internal_server_error"
    assert payload["error"]["message"] == "An internal server error occurred."
    assert payload["error"]["retryable"] is True
    assert "private founder payload" not in response.text


def test_http_500_detail_does_not_echo_private_exception_text() -> None:
    test_app = create_app()

    @test_app.get("/api/v1/_test-http-500")
    async def _test_http_500() -> None:
        raise HTTPException(status_code=500, detail="private founder payload must not escape")

    with TestClient(test_app) as client:
        response = client.get("/api/v1/_test-http-500")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "private founder payload" not in response.text


def test_unknown_routes_use_the_same_v1_not_found_envelope() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/_route-that-does-not-exist")

    payload = response.json()
    assert response.status_code == 404
    assert payload["version"] == "v1"
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["retryable"] is False
