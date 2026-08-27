from fastapi.testclient import TestClient

from api import app


client = TestClient(app)


# ============================================================
# ROOT
# ============================================================

def test_root():

    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "strict-rag"
    assert data["status"] == "ok"


# ============================================================
# HEALTH
# ============================================================

def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "strict-rag"


# ============================================================
# READINESS
# ============================================================

def test_ready():

    response = client.get("/ready")

    # Local development should normally be ready.
    # If the local Qdrant index is unavailable,
    # 503 is also a valid readiness response.

    assert response.status_code in (
        200,
        503,
    )

    data = response.json()

    assert "status" in data


# ============================================================
# INPUT VALIDATION
# ============================================================

def test_empty_question_is_rejected():

    response = client.post(

        "/api/v1/chat",

        json={
            "question": ""
        }
    )

    assert response.status_code == 422


def test_question_too_long_is_rejected():

    response = client.post(

        "/api/v1/chat",

        json={
            "question": "a" * 2001
        }
    )

    assert response.status_code == 422


# ============================================================
# REQUEST ID
# ============================================================

def test_request_id_is_returned():

    response = client.get("/health")

    assert response.status_code == 200

    # Middleware should generate this.
    assert response.headers.get(
        "X-Request-ID"
    )


def test_custom_request_id_is_preserved():

    request_id = "test-request-123"

    response = client.get(

        "/health",

        headers={
            "X-Request-ID": request_id
        }
    )

    assert response.status_code == 200

    assert response.headers.get(
        "X-Request-ID"
    ) == request_id


# ============================================================
# CHAT RESPONSE CONTRACT
# ============================================================

def test_chat_response_contract(
    monkeypatch
):

    def fake_answer_question(
        question
    ):

        return {
            "success": True,

            "answer": (
                "Test documentation answer."
            ),

            "sources": [
                {
                    "chunk_id": "secret-source",
                    "relevance": 0.99,
                }
            ],

            "_error": {
                "stage": "test",
                "reason": "secret"
            }
        }

    monkeypatch.setattr(
        "api.answer_question",
        fake_answer_question
    )

    response = client.post(

        "/api/v1/chat",

        json={
            "question": "Test question"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert data["answer"] == (
        "Test documentation answer."
    )

    assert "sources" not in data

    assert "_error" not in data


# ============================================================
# FAILED RAG RESPONSE
# ============================================================

def test_failed_rag_response(
    monkeypatch
):

    def fake_answer_question(
        question
    ):

        return {
            "success": False,

            "answer": (
                "I couldn't provide a reliable "
                "answer from the available documentation."
            ),

            "sources": [],

            "_error": {
                "stage": "verification",
                "reason": "internal diagnostic"
            }
        }

    monkeypatch.setattr(
        "api.answer_question",
        fake_answer_question
    )

    response = client.post(

        "/api/v1/chat",

        json={
            "question": "Unknown question"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is False

    assert "sources" not in data

    assert "_error" not in data

    assert data["error"] is not None


# ============================================================
# INTERNAL EXCEPTION
# ============================================================

def test_internal_exception_is_hidden(
    monkeypatch
):

    def fake_answer_question(
        question
    ):

        raise RuntimeError(
            "SECRET GROQ API ERROR"
        )

    monkeypatch.setattr(
        "api.answer_question",
        fake_answer_question
    )

    response = client.post(

        "/api/v1/chat",

        json={
            "question": "Test question"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is False

    assert (
        "SECRET GROQ API ERROR"
        not in response.text
    )

    assert (
        "SECRET GROQ API ERROR"
        not in data["answer"]
    )

    assert (
        data["request_id"]
        is not None
    )