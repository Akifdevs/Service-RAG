import logging
import os
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_pipeline import answer_question


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("strict-rag-api")


# ============================================================
# CONFIGURATION
# ============================================================

SERVICE_NAME = "strict-rag"
API_VERSION = "1.0.0"

DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000,"
    "http://localhost:5173,"
    "http://127.0.0.1:3000,"
    "http://127.0.0.1:5173"
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        DEFAULT_ALLOWED_ORIGINS,
    ).split(",")
    if origin.strip()
]


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Strict Documentation RAG API",
    description=(
        "Documentation-grounded question answering API. "
        "Answers are returned only after retrieval, "
        "generation, source validation, and claim verification."
    ),
    version=API_VERSION,
)


# ============================================================
# CORS
# ============================================================

# ------------------------------------------------------------
# Development:
#
# The frontend normally runs on:
#
#   http://localhost:5173
#   http://127.0.0.1:5173
#
# We allow both localhost and 127.0.0.1.
#
# In production, set:
#
# ALLOWED_ORIGINS=https://your-frontend-domain.com
#
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,

    allow_origins=ALLOWED_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's documentation question.",
    )


# ============================================================
# RESPONSE MODEL
# ============================================================

class ChatResponse(BaseModel):

    success: bool

    answer: str

    error: Optional[str] = None

    request_id: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root() -> Dict[str, str]:

    return {
        "service": SERVICE_NAME,
        "status": "ok",
        "version": API_VERSION,
        "environment": os.getenv(
            "ENVIRONMENT",
            "development",
        ),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health() -> Dict[str, str]:

    return {
        "status": "ok",
        "service": SERVICE_NAME,
    }


# ============================================================
# READINESS CHECK
# ============================================================

@app.get("/ready")
def ready() -> Dict[str, str]:

    try:

        from ingestion.manifest import (
            get_active_collection_name,
        )

        collection_name = (
            get_active_collection_name()
        )

        if not collection_name:

            return {
                "status": "not_ready",
                "service": SERVICE_NAME,
                "collection": "none",
            }

        return {
            "status": "ready",
            "service": SERVICE_NAME,
            "collection": collection_name,
        }

    except Exception:

        logger.exception(
            "Readiness check failed."
        )

        return {
            "status": "not_ready",
            "service": SERVICE_NAME,
            "collection": "unknown",
        }


# ============================================================
# INTERNAL CHAT HANDLER
# ============================================================

def process_chat(
    request: ChatRequest,
    request_id: str,
) -> ChatResponse:

    question = request.question.strip()

    logger.info(
        "Chat request received | request_id=%s",
        request_id,
    )

    # --------------------------------------------------------
    # Input validation
    # --------------------------------------------------------

    if not question:

        logger.warning(
            "Empty question | request_id=%s",
            request_id,
        )

        return ChatResponse(
            success=False,
            answer=(
                "Please enter a question about "
                "the service documentation."
            ),
            error="invalid_request",
            request_id=request_id,
        )

    # --------------------------------------------------------
    # RAG pipeline
    # --------------------------------------------------------

    try:

        result = answer_question(
            question
        )

    except Exception:

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Never expose internal:
        #
        # - Qdrant errors
        # - Hugging Face errors
        # - Groq errors
        # - Python exceptions
        # - file paths
        # - stack traces
        #
        # to the frontend.
        # ----------------------------------------------------

        logger.exception(
            "RAG pipeline failed | request_id=%s",
            request_id,
        )

        return ChatResponse(
            success=False,
            answer=(
                "I couldn't provide a reliable answer "
                "from the available documentation."
            ),
            error="rag_service_error",
            request_id=request_id,
        )

    # --------------------------------------------------------
    # Extract result safely
    # --------------------------------------------------------

    success = bool(
        result.get(
            "success",
            False,
        )
    )

    answer = str(
        result.get(
            "answer",
            "I couldn't provide a reliable answer "
            "from the available documentation.",
        )
    )

    # --------------------------------------------------------
    # RAG refusal
    # --------------------------------------------------------

    if not success:

        logger.info(
            "RAG refused answer | request_id=%s",
            request_id,
        )

        return ChatResponse(
            success=False,
            answer=answer,
            error="answer_not_available",
            request_id=request_id,
        )

    # --------------------------------------------------------
    # Successful response
    # --------------------------------------------------------

    logger.info(
        "Chat request completed successfully | "
        "request_id=%s",
        request_id,
    )

    return ChatResponse(
        success=True,
        answer=answer,
        error=None,
        request_id=request_id,
    )


# ============================================================
# VERSIONED CHAT ENDPOINT
# ============================================================

@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
)
def chat_v1(
    request: ChatRequest,
    http_request: Request,
) -> ChatResponse:

    # --------------------------------------------------------
    # Allow frontend to provide an ID if desired.
    #
    # Otherwise generate one.
    # --------------------------------------------------------

    request_id = (
        http_request.headers.get(
            "X-Request-ID"
        )
        or str(uuid.uuid4())
    )

    return process_chat(
        request,
        request_id,
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat_legacy(
    request: ChatRequest,
    http_request: Request,
) -> ChatResponse:

    request_id = (
        http_request.headers.get(
            "X-Request-ID"
        )
        or str(uuid.uuid4())
    )

    return process_chat(
        request,
        request_id,
    )