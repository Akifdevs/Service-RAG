import logging
from typing import Any, Dict, List


# ============================================================
# CONFIGURATION
# ============================================================

REFUSAL_MESSAGE = (
    "I'm not confident enough in the available information to "
"answer that accurately. Could you try rephrasing, or ask "
"something else about the Service Order Section?"
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# RESULT BUILDERS
# ============================================================

def success_result(
    answer: str,
    sources: List[Dict[str, Any]]
) -> Dict[str, Any]:

    return {
        "success": True,
        "answer": answer,
        "sources": sources
    }


def failure_result(
    stage: str,
    reason: str = ""
) -> Dict[str, Any]:

    result = {
        "success": False,
        "answer": REFUSAL_MESSAGE,
        "sources": []
    }

    # Internal diagnostic information.
    # This can be logged by an API layer rather than
    # exposed directly to end users.
    if reason:
        result["_error"] = {
            "stage": stage,
            "reason": reason
        }

    return result


# ============================================================
# SOURCE EXTRACTION
# ============================================================

def build_sources(
    retrieval_result
) -> List[Dict[str, Any]]:

    sources = []

    for result in retrieval_result.get(
        "results",
        []
    ):

        payload = result.payload

        sources.append({

            "chunk_id":
                payload.get(
                    "chunk_id"
                ),

            "document":
                payload.get(
                    "document"
                ),

            "heading":
                payload.get(
                    "heading"
                ),

            "heading_path":
                payload.get(
                    "heading_path",
                    []
                ),

            "relevance":
                round(
                    float(result.score),
                    4
                ),

            "start_line":
                payload.get(
                    "start_line"
                ),

            "end_line":
                payload.get(
                    "end_line"
                )
        })

    return sources


# ============================================================
# CONTEXT SOURCE IDs
# ============================================================

def extract_context_source_ids(
    context: str
) -> set:

    source_ids = set()

    lines = context.splitlines()

    for index, line in enumerate(lines):

        if line.strip() == "Source Chunk ID:":

            if index + 1 < len(lines):

                source_id = (
                    lines[index + 1]
                    .strip()
                )

                if source_id:
                    source_ids.add(
                        source_id
                    )

    return source_ids


# ============================================================
# GENERATED CLAIM VALIDATION
# ============================================================

def validate_generated_claims(
    claims,
    context
):

    valid_source_ids = (
        extract_context_source_ids(
            context
        )
    )

    if not valid_source_ids:

        raise ValueError(
            "Retrieved context contains no "
            "valid source chunk IDs."
        )

    if not claims:

        raise ValueError(
            "Generated answer contains no claims."
        )

    for index, claim in enumerate(
        claims,
        start=1
    ):

        if not isinstance(
            claim,
            dict
        ):

            raise ValueError(
                f"Claim #{index} is not an object."
            )

        claim_text = claim.get(
            "text"
        )

        source_id = claim.get(
            "source_chunk_id"
        )

        if not claim_text:

            raise ValueError(
                f"Claim #{index} has no text."
            )

        if not source_id:

            raise ValueError(
                f"Claim #{index} has no source_chunk_id."
            )

        source_id = source_id.strip()

        # ----------------------------------------------------
        # Never allow SOURCE 1 / SOURCE 2 / etc.
        # ----------------------------------------------------

        if source_id.upper().startswith(
            "SOURCE "
        ):

            raise ValueError(
                f"Claim #{index} uses invalid "
                f"source ID: {source_id}"
            )

        # ----------------------------------------------------
        # Source must actually exist in retrieved context.
        # ----------------------------------------------------

        if source_id not in valid_source_ids:

            raise ValueError(
                f"Claim #{index} references a source "
                f"that was not retrieved: {source_id}"
            )

    return True


# ============================================================
# VERIFIER RESULT VALIDATION
# ============================================================

def validate_verification_result(
    verification,
    context
):

    if not isinstance(
        verification,
        dict
    ):

        raise ValueError(
            "Verifier returned an invalid result."
        )

    if not isinstance(
        verification.get("verified"),
        bool
    ):

        raise ValueError(
            "Verifier result does not contain "
            "a valid 'verified' field."
        )

    if not verification.get(
        "verified"
    ):

        return False

    claims = verification.get(
        "claims",
        []
    )

    if not claims:

        raise ValueError(
            "Verifier marked the answer verified "
            "but returned no claims."
        )

    valid_source_ids = (
        extract_context_source_ids(
            context
        )
    )

    for index, claim in enumerate(
        claims,
        start=1
    ):

        if not claim.get(
            "supported",
            False
        ):

            return False

        source_id = claim.get(
            "source_chunk_id",
            ""
        ).strip()

        if not source_id:

            raise ValueError(
                f"Verifier claim #{index} "
                "has no source ID."
            )

        if source_id not in valid_source_ids:

            raise ValueError(
                f"Verifier claim #{index} "
                f"references unknown source: "
                f"{source_id}"
            )

    return True


# ============================================================
# MAIN RAG FUNCTION
# ============================================================

def answer_question(
    question: str
) -> Dict[str, Any]:
    """
    Execute the complete strict RAG pipeline.

    This is the main function that an API layer,
    chatbot backend, or application should call.

    Returns a JSON-serializable dictionary.
    """

    question = question.strip()

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    if not question:

        return failure_result(
            stage="input",
            reason="Question is empty."
        )

    # ========================================================
    # STEP 1: RETRIEVAL
    # ========================================================

    try:

        from retrieval.retrieval import retrieve

        retrieval_result = retrieve(
            question
        )

    except Exception as error:

        logger.exception(
            "RAG retrieval failed."
        )

        return failure_result(
            stage="retrieval",
            reason=str(error)
        )

    # --------------------------------------------------------
    # Relevance gate
    # --------------------------------------------------------

    if not retrieval_result.get(
        "has_evidence",
        False
    ):

        return failure_result(
            stage="retrieval",
            reason=(
                "No sufficiently relevant "
                "documentation found."
            )
        )

    results = retrieval_result.get(
        "results",
        []
    )

    context = retrieval_result.get(
        "context",
        ""
    )

    if not results:

        return failure_result(
            stage="retrieval",
            reason=(
                "Retriever returned no evidence."
            )
        )

    if not context.strip():

        return failure_result(
            stage="retrieval",
            reason=(
                "Retriever returned empty context."
            )
        )

    # ========================================================
    # STEP 2: GENERATION
    # ========================================================

    try:

        from generation.generator import (
            generate_answer
        )

        generation_result = generate_answer(

            question,

            context

        )

    except Exception as error:

        logger.exception(
            "RAG generation failed."
        )

        return failure_result(
            stage="generation",
            reason=str(error)
        )

    # --------------------------------------------------------
    # Generator refusal
    # --------------------------------------------------------

    if not generation_result.get(
        "answerable",
        False
    ):

        return failure_result(
            stage="generation",
            reason=(
                "Generator determined that the "
                "documentation does not contain "
                "enough information."
            )
        )

    answer = generation_result.get(
        "answer",
        ""
    )

    claims = generation_result.get(
        "claims",
        []
    )

    if not answer.strip():

        return failure_result(
            stage="generation",
            reason=(
                "Generator returned an empty answer."
            )
        )

    # ========================================================
    # STEP 3: SOURCE VALIDATION
    # ========================================================

    try:

        validate_generated_claims(
            claims,
            context
        )

    except Exception as error:

        logger.exception(
            "Generated source validation failed."
        )

        return failure_result(
            stage="source_validation",
            reason=str(error)
        )

    # ========================================================
    # STEP 4: CLAIM VERIFICATION
    # ========================================================

    try:

        from generation.verifier import (
            verify_answer
        )

        verification = verify_answer(

            question=question,

            answer=answer,

            claims=claims,

            context=context

        )

    except Exception as error:

        logger.exception(
            "RAG verification failed."
        )

        return failure_result(
            stage="verification",
            reason=str(error)
        )

    # ========================================================
    # STEP 5: FINAL FAIL-CLOSED CHECK
    # ========================================================

    try:

        verified = validate_verification_result(
            verification,
            context
        )

    except Exception as error:

        logger.exception(
            "Final verification validation failed."
        )

        return failure_result(
            stage="verification",
            reason=str(error)
        )

    if not verified:

        return failure_result(
            stage="verification",
            reason=(
                "One or more generated claims "
                "were not supported by the "
                "documentation."
            )
        )

    # ========================================================
    # STEP 6: BUILD PUBLIC RESPONSE
    # ========================================================

    sources = build_sources(
        retrieval_result
    )

    return success_result(
        answer=answer,
        sources=sources
    )


# ============================================================
# API-FRIENDLY HEALTH CHECK
# ============================================================

def health_check() -> Dict[str, Any]:
    """
    Basic health check for the RAG service.

    This does not call the LLM or embedding API.
    """

    return {
        "status": "ok",
        "service": "strict-rag"
    }


# ============================================================
# TERMINAL TEST MODE
# ============================================================

def main():

    print("=" * 70)
    print("STRICT PRODUCTION RAG PIPELINE")
    print("=" * 70)

    question = input(
        "\nEnter your question: "
    ).strip()

    result = answer_question(
        question
    )

    print()
    print("=" * 70)
    print("RAG RESPONSE")
    print("=" * 70)

    print()
    print(
        f"Success: {result['success']}"
    )

    print()
    print(
        f"Answer: {result['answer']}"
    )

    # --------------------------------------------------------
    # Development diagnostics
    # --------------------------------------------------------

    if result.get("_error"):

        print()
        print(
            "Internal diagnostic:"
        )

        print(
            result["_error"]
        )

    # --------------------------------------------------------
    # Sources
    # --------------------------------------------------------

    if result.get("sources"):

        print()
        print("Sources:")

        for index, source in enumerate(
            result["sources"],
            start=1
        ):

            path = " > ".join(
                source.get(
                    "heading_path",
                    []
                )
            )

            print()
            print(
                f"{index}. {path}"
            )

            print(
                f"   Chunk ID: "
                f"{source['chunk_id']}"
            )

            print(
                f"   Relevance: "
                f"{source['relevance']:.4f}"
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()