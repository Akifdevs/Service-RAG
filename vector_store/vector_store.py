import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "embedded_chunks.json"

QDRANT_PATH = (
    BASE_DIR
    / "vector_store"
    / "qdrant_data"
)


# =========================================================
# Qdrant Configuration
# =========================================================

COLLECTION_NAME = "service_order"

VECTOR_SIZE = 384

DISTANCE = Distance.COSINE


# =========================================================
# Load embedded chunks
# =========================================================

def load_embedded_chunks(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"Embedded chunks file not found:\n"
            f"{file_path}\n\n"
            "Run embedder.py first."
        )

    with file_path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# =========================================================
# Create persistent Qdrant client
# =========================================================

def create_qdrant_client():

    QDRANT_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    client = QdrantClient(
        path=str(QDRANT_PATH)
    )

    return client


# =========================================================
# Create collection
# =========================================================

def create_collection(client):

    if client.collection_exists(
        collection_name=COLLECTION_NAME
    ):

        print(
            f"Collection '{COLLECTION_NAME}' "
            f"already exists."
        )

        return

    client.create_collection(

        collection_name=COLLECTION_NAME,

        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=DISTANCE
        )
    )

    print(
        f"Collection '{COLLECTION_NAME}' created."
    )


# =========================================================
# Create Qdrant points
# =========================================================

def create_points(chunks):

    points = []

    for index, chunk in enumerate(chunks):

        point = PointStruct(

            id=index,

            vector=chunk["embedding"],

            payload={

                "chunk_id":
                    chunk["chunk_id"],

                "document":
                    chunk["document"]
                    if "document" in chunk
                    else "service-order-rag.md",

                "heading":
                    chunk["heading"],

                "heading_level":
                    chunk["heading_level"],

                "heading_path":
                    chunk["heading_path"],

                "content":
                    chunk["content"],

                "text":
                    chunk["text"],

                "start_line":
                    chunk["start_line"],

                "end_line":
                    chunk["end_line"],
            }
        )

        points.append(point)

    return points


# =========================================================
# Insert / update vectors
# =========================================================

def insert_points(client, points):

    client.upsert(

        collection_name=COLLECTION_NAME,

        points=points
    )

    print(
        f"Inserted/updated {len(points)} vectors."
    )


# =========================================================
# Verify collection
# =========================================================

def verify_collection(client):

    collection_info = client.get_collection(
        collection_name=COLLECTION_NAME
    )

    print("\nCollection information:")

    print(
        f"Vectors stored: "
        f"{collection_info.points_count}"
    )


# =========================================================
# Main
# =========================================================

def main():

    print("=" * 60)
    print("PERSISTENT QDRANT VECTOR STORE")
    print("=" * 60)

    # -----------------------------------------------------
    # Load embeddings
    # -----------------------------------------------------

    print(
        f"\nLoading:\n{INPUT_FILE}"
    )

    chunks = load_embedded_chunks(
        INPUT_FILE
    )

    print(
        f"Loaded {len(chunks)} embedded chunks."
    )

    # -----------------------------------------------------
    # Create persistent client
    # -----------------------------------------------------

    print(
        f"\nQdrant storage location:\n"
        f"{QDRANT_PATH}"
    )

    client = create_qdrant_client()

    print(
        "Persistent Qdrant client created."
    )

    # -----------------------------------------------------
    # Create collection
    # -----------------------------------------------------

    print(
        f"\nChecking collection: "
        f"{COLLECTION_NAME}"
    )

    create_collection(client)

    # -----------------------------------------------------
    # Prepare points
    # -----------------------------------------------------

    print("\nPreparing vectors...")

    points = create_points(chunks)

    print(
        f"Prepared {len(points)} points."
    )

    # -----------------------------------------------------
    # Insert
    # -----------------------------------------------------

    print("\nUploading vectors...")

    insert_points(
        client,
        points
    )

    # -----------------------------------------------------
    # Verify
    # -----------------------------------------------------

    verify_collection(client)

    # -----------------------------------------------------
    # Final information
    # -----------------------------------------------------

    print("\n" + "=" * 60)
    print("PERSISTENT VECTOR STORE READY")
    print("=" * 60)

    print(
        f"\nCollection: "
        f"{COLLECTION_NAME}"
    )

    print(
        f"Vector size: "
        f"{VECTOR_SIZE}"
    )

    print(
        "Distance: COSINE"
    )

    print(
        f"Vectors: "
        f"{len(points)}"
    )

    print(
        f"\nDatabase location:\n"
        f"{QDRANT_PATH}"
    )

    print(
        "\nThe vectors will remain stored "
        "after this program exits."
    )

    client.close()


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":
    main()