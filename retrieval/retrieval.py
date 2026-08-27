import os
from pathlib import Path

from huggingface_hub import InferenceClient
from qdrant_client import QdrantClient

from ingestion.manifest import (
    EMBEDDING_MODEL,
    get_active_collection_name,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

QDRANT_PATH = (
    BASE_DIR
    / "vector_store"
    / "qdrant_data"
)

DEFAULT_TOP_K = 5

DEFAULT_MIN_SCORE = 0.70


# ============================================================
# CLIENTS
# ============================================================

def create_huggingface_client():

    token = os.getenv(
        "HF_TOKEN"
    )

    if not token:

        raise RuntimeError(
            "HF_TOKEN is not set."
        )

    return InferenceClient(
        provider="hf-inference",
        api_key=token
    )


def create_qdrant_client():

    return QdrantClient(
        path=str(QDRANT_PATH)
    )


# ============================================================
# ACTIVE COLLECTION
# ============================================================

def get_active_collection(
    qdrant
):
    """
    Get the currently active Qdrant collection
    from the indexing manifest.

    The manifest is the source of truth.
    """

    collection_name = (
        get_active_collection_name()
    )

    if not collection_name:

        raise RuntimeError(
            "No active RAG index is available.\n\n"
            "Run the document synchronization process first."
        )

    if not qdrant.collection_exists(
        collection_name=collection_name
    ):

        raise RuntimeError(
            "The active RAG collection does not exist.\n\n"
            f"Collection: {collection_name}\n\n"
            "Run the document synchronization process."
        )

    return collection_name


# ============================================================
# EMBEDDING
# ============================================================

def generate_query_embedding(
    hf_client,
    text
):

    embedding = hf_client.feature_extraction(
        text,
        model=EMBEDDING_MODEL
    )

    return embedding.tolist()


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_context(
    results
):

    context_parts = []

    for index, result in enumerate(
        results,
        start=1
    ):

        payload = result.payload

        chunk_id = payload.get(
            "chunk_id"
        )

        heading = payload.get(
            "heading",
            ""
        )

        heading_path = payload.get(
            "heading_path",
            []
        )

        content = payload.get(
            "content",
            ""
        )

        context_parts.append(

            f"SOURCE {index}\n\n"

            f"Source Chunk ID:\n"
            f"{chunk_id}\n\n"

            f"Heading:\n"
            f"{heading}\n\n"

            f"Heading Path:\n"
            f"{' > '.join(heading_path)}\n\n"

            f"Content:\n"
            f"{content}"
        )

    return (
        "\n\n"
        + "\n\n".join(
            context_parts
        )
    )


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve(
    query,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE
):

    query = query.strip()

    if not query:

        return {
            "query": query,
            "has_evidence": False,
            "results": [],
            "context": "",
            "collection_name": None
        }

    hf_client = None
    qdrant = None

    try:

        # ----------------------------------------------------
        # Clients
        # ----------------------------------------------------

        hf_client = (
            create_huggingface_client()
        )

        qdrant = (
            create_qdrant_client()
        )

        # ----------------------------------------------------
        # Determine active collection
        # ----------------------------------------------------

        collection_name = (
            get_active_collection(
                qdrant
            )
        )

        # ----------------------------------------------------
        # Query embedding
        # ----------------------------------------------------

        query_vector = (
            generate_query_embedding(
                hf_client,
                query
            )
        )

        # ----------------------------------------------------
        # Validate embedding dimension
        # ----------------------------------------------------

        if len(query_vector) != 384:

            raise RuntimeError(
                "Query embedding dimension mismatch.\n"
                f"Expected: 384\n"
                f"Received: {len(query_vector)}"
            )

        # ----------------------------------------------------
        # Qdrant search
        # ----------------------------------------------------

        results = qdrant.query_points(

            collection_name=collection_name,

            query=query_vector,

            limit=top_k,

            with_payload=True

        ).points

        # ----------------------------------------------------
        # Relevance gate
        # ----------------------------------------------------

        filtered_results = [

            result

            for result in results

            if result.score >= min_score

        ]

        if not filtered_results:

            return {

                "query":
                    query,

                "has_evidence":
                    False,

                "results":
                    [],

                "context":
                    "",

                "collection_name":
                    collection_name
            }

        # ----------------------------------------------------
        # Build context
        # ----------------------------------------------------

        context = build_context(
            filtered_results
        )

        return {

            "query":
                query,

            "has_evidence":
                True,

            "results":
                filtered_results,

            "context":
                context,

            "collection_name":
                collection_name
        }

    finally:

        if qdrant is not None:

            qdrant.close()


# ============================================================
# TERMINAL TEST
# ============================================================

def main():

    print("=" * 70)
    print("STRICT RAG RETRIEVER")
    print("=" * 70)

    question = input(
        "\nEnter your question: "
    ).strip()

    try:

        result = retrieve(
            question
        )

    except Exception as error:

        print()
        print(
            "Retrieval error:"
        )

        print(error)

        return

    # --------------------------------------------------------
    # No evidence
    # --------------------------------------------------------

    if not result["has_evidence"]:

        print()
        print(
            "No sufficiently relevant documentation found."
        )

        return

    # --------------------------------------------------------
    # Active collection
    # --------------------------------------------------------

    print()
    print(
        f"Active collection: "
        f"{result['collection_name']}"
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RETRIEVAL")
    print("=" * 70)

    for index, result_point in enumerate(
        result["results"],
        start=1
    ):

        payload = result_point.payload

        print()
        print(
            f"Result #{index}"
        )

        print(
            f"Score: "
            f"{result_point.score:.4f}"
        )

        print(
            "Chunk ID: "
            f"{payload.get('chunk_id')}"
        )

        print(
            "Heading: "
            f"{payload.get('heading')}"
        )

        print(
            "Path: "
            + " > ".join(
                payload.get(
                    "heading_path",
                    []
                )
            )
        )

    print()
    print(
        "Evidence passed relevance gate."
    )

    print(
        f"Chunks passed: "
        f"{len(result['results'])}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()