import logging
import os
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_pipeline import answer_question


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("strict-rag-api")


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
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

# Development configuration.
# Restrict this to your actual frontend origin in production.

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
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


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health() -> Dict[str, str]:

    return {
        "status": "ok",
        "service": "strict-rag",
    }


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest) -> ChatResponse:

    question = request.question.strip()

    logger.info(
        "Received chat request."
    )

    try:

        result = answer_question(
            question
        )

    except Exception:

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Never expose internal RAG, Qdrant, HF, or Groq
        # errors to the frontend.
        # ----------------------------------------------------

        logger.exception(
            "RAG pipeline failed."
        )

        return ChatResponse(
            success=False,
            answer=(
                "I couldn't provide a reliable answer "
                "from the available documentation."
            ),
        )

    # --------------------------------------------------------
    # SECURITY BOUNDARY
    # --------------------------------------------------------
    #
    # We intentionally expose ONLY:
    #
    #   success
    #   answer
    #
    # Internal sources, scores, claims, verification results,
    # diagnostics, and retrieved context stay inside the
    # backend.
    # --------------------------------------------------------

    return ChatResponse(
        success=bool(result.get("success", False)),
        answer=str(
            result.get(
                "answer",
                "I couldn't provide a reliable answer "
                "from the available documentation.",
            )
        ),
    )