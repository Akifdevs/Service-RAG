import os
from typing import List


# ============================================================
# APPLICATION
# ============================================================

APP_NAME = os.getenv(
    "APP_NAME",
    "Strict Documentation RAG API"
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    "1.0.0"
)

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development"
).lower()


# ============================================================
# SERVER
# ============================================================

HOST = os.getenv(
    "HOST",
    "127.0.0.1"
)

PORT = int(
    os.getenv(
        "PORT",
        "8000"
    )
)


# ============================================================
# CORS
# ============================================================

def get_allowed_origins() -> List[str]:

    raw_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    )

    origins = [
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    ]

    return origins


ALLOWED_ORIGINS = get_allowed_origins()


# ============================================================
# API
# ============================================================

API_PREFIX = "/api/v1"

CHAT_MAX_LENGTH = int(
    os.getenv(
        "CHAT_MAX_LENGTH",
        "2000"
    )
)


# ============================================================
# RAG
# ============================================================

REFUSAL_MESSAGE = (
   "I'm not confident enough in the available information to "
"answer that accurately. Could you try rephrasing, or ask "
"something else about the Service Order Section?"
)