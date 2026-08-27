import logging
import uuid
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import (
    API_PREFIX,
    APP_NAME,
    APP_VERSION,
    ALLOWED_ORIGINS,
    CHAT_MAX_LENGTH,
    ENVIRONMENT,
    REFUSAL_MESSAGE,
)

from rag_pipeline import answer_question


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "strict-rag-api"
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(

    title=APP_NAME,

    description=(
        "Documentation-grounded question answering API. "
        "Answers are returned only after retrieval, "
        "generation, source validation, and claim verification."
    ),

    version=APP_VERSION,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=ALLOWED_ORIGINS,

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],

    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
    ],
)


# ============================================================
# REQUEST ID MIDDLEWARE
# ============================================================

@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next
):

    request_id = (
        request.headers.get(
            "X-Request-ID"
        )
        or str(uuid.uuid4())
    )

    request.state.request_id = (
        request_id
    )

    try:

        response = await call_next(
            request
        )

    except Exception:

        logger.exception(
            "Unhandled request failure | "
            "request_id=%s | "
            "method=%s | "
            "path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        response = JSONResponse(

            status_code=500,

            content={
                "success": False,
                "answer": REFUSAL_MESSAGE,
                "error": "Internal server error.",
                "request_id": request_id,
            },
        )

    response.headers[
        "X-Request-ID"
    ] = request_id

    return response


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):

    question: str = Field(

        ...,

        min_length=1,

        max_length=CHAT_MAX_LENGTH,

        description=(
            "User's documentation question."
        ),
    )


# ============================================================
# RESPONSE MODEL
# ============================================================

class ChatResponse(BaseModel):

    success: bool

    answer: str

    error: str | None = None

    request_id: str | None = None


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root() -> Dict[str, str]:

    return {
        "service": "strict-rag",
        "status": "ok",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health() -> Dict[str, str]:

    """
    Liveness check.

    This endpoint only confirms that the API
    process is alive.
    """

    return {
        "status": "ok",
        "service": "strict-rag",
    }


# ============================================================
# READINESS
# ============================================================

@app.get("/ready")
def readiness():

    """
    Readiness check.

    Confirms that the RAG system has an active
    indexed collection available.
    """

    try:

        from ingestion.manifest import (
            get_active_collection_name
        )

        collection_name = (
            get_active_collection_name()
        )

        if not collection_name:

            return JSONResponse(

                status_code=503,

                content={
                    "status": "not_ready",
                    "reason": (
                        "No active RAG collection."
                    ),
                },
            )

        from vector_store.vector_store import (
            create_qdrant_client
        )

        client = (
            create_qdrant_client()
        )

        try:

            exists = (
                client.collection_exists(
                    collection_name=
                        collection_name
                )
            )

            if not exists:

                return JSONResponse(

                    status_code=503,

                    content={
                        "status": "not_ready",
                        "reason": (
                            "Active RAG collection "
                            "does not exist."
                        ),
                    },
                )

            collection_info = (
                client.get_collection(
                    collection_name=
                        collection_name
                )
            )

            if not collection_info.points_count:

                return JSONResponse(

                    status_code=503,

                    content={
                        "status": "not_ready",
                        "reason": (
                            "Active RAG collection "
                            "contains no vectors."
                        ),
                    },
                )

        finally:

            client.close()

        return {
            "status": "ready",
            "service": "strict-rag",
            "collection": collection_name,
        }

    except Exception:

        logger.exception(
            "Readiness check failed."
        )

        return JSONResponse(

            status_code=503,

            content={
                "status": "not_ready",
                "reason": (
                    "RAG dependencies are unavailable."
                ),
            },
        )


# ============================================================
# CHAT
# ============================================================

@app.post(
    f"{API_PREFIX}/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    http_request: Request,
) -> ChatResponse:

    question = (
        request.question.strip()
    )

    request_id = getattr(
        http_request.state,
        "request_id",
        None
    )

    logger.info(

        "Chat request received | "
        "request_id=%s | "
        "question_length=%d",

        request_id,

        len(question),
    )

    try:

        result = answer_question(
            question
        )

    except Exception:

        logger.exception(

            "RAG pipeline failed | "
            "request_id=%s",

            request_id,
        )

        return ChatResponse(

            success=False,

            answer=REFUSAL_MESSAGE,

            error=(
                "Unable to process the request."
            ),

            request_id=request_id,
        )

    success = bool(
        result.get(
            "success",
            False
        )
    )

    answer = str(
        result.get(
            "answer",
            REFUSAL_MESSAGE
        )
    )

    # --------------------------------------------------------
    # IMPORTANT SECURITY BOUNDARY
    # --------------------------------------------------------
    #
    # Sources, scores, retrieved context,
    # claims, verifier output, and internal
    # diagnostics NEVER leave the API.
    # --------------------------------------------------------

    if success:

        logger.info(

            "Chat request completed | "
            "request_id=%s | "
            "success=true",

            request_id,
        )

        return ChatResponse(

            success=True,

            answer=answer,

            error=None,

            request_id=request_id,
        )

    logger.warning(

        "Chat request rejected | "
        "request_id=%s",

        request_id,
    )

    return ChatResponse(

        success=False,

        answer=REFUSAL_MESSAGE,

        error=(
            "The documentation did not provide "
            "a sufficiently reliable answer."
        ),

        request_id=request_id,
    )