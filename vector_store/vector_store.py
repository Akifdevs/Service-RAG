import json
import re
from pathlib import Path
from typing import List


from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = (
    Path(__file__).resolve().parent.parent
)

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "embedded_chunks.json"
)

QDRANT_PATH = (
    BASE_DIR
    / "vector_store"
    / "qdrant_data"
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_COLLECTION_NAME = "service_order"

VECTOR_SIZE = 384

DISTANCE = Distance.COSINE


# ============================================================
# CLIENT
# ============================================================

def create_qdrant_client():

    QDRANT_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    return QdrantClient(
        path=str(QDRANT_PATH)
    )


# ============================================================
# COLLECTION NAME
# ============================================================

def build_collection_name(
    index_version: int
) -> str:

    return (
        f"{BASE_COLLECTION_NAME}_v"
        f"{index_version}"
    )


# ============================================================
# VERSION PARSING
# ============================================================

def get_collection_version(
    collection_name: str
):

    pattern = (
        rf"^{re.escape(BASE_COLLECTION_NAME)}_v(\d+)$"
    )

    match = re.match(
        pattern,
        collection_name
    )

    if not match:

        return None

    return int(
        match.group(1)
    )


# ============================================================
# LOAD EMBEDDINGS
# ============================================================

def load_embedded_chunks(
    file_path=INPUT_FILE
):

    if not file_path.exists():

        raise FileNotFoundError(
            f"Embedded chunks file not found:\n"
            f"{file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# CREATE COLLECTION
# ============================================================

def create_collection(
    client,
    collection_name: str
):

    if client.collection_exists(
        collection_name=collection_name
    ):

        return

    client.create_collection(

        collection_name=collection_name,

        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=DISTANCE
        )
    )


# ============================================================
# CREATE POINTS
# ============================================================

def create_points(
    chunks: List[dict]
):

    points = []

    for index, chunk in enumerate(
        chunks
    ):

        point = PointStruct(

            id=index,

            vector=chunk["embedding"],

            payload={

                "chunk_id":
                    chunk["chunk_id"],

                "document":
                    chunk.get(
                        "document",
                        "service-order-rag.md"
                    ),

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
                    chunk["end_line"]
            }
        )

        points.append(
            point
        )

    return points


# ============================================================
# INSERT POINTS
# ============================================================

def insert_points(
    client,
    collection_name: str,
    points
):

    if not points:

        raise ValueError(
            "Cannot insert zero points."
        )

    client.upsert(

        collection_name=collection_name,

        points=points
    )


# ============================================================
# VERIFY COLLECTION
# ============================================================

def verify_collection(
    client,
    collection_name: str,
    expected_count: int
):

    if not client.collection_exists(
        collection_name=collection_name
    ):

        raise RuntimeError(
            f"Collection does not exist:\n"
            f"{collection_name}"
        )

    info = client.get_collection(
        collection_name=collection_name
    )

    actual_count = (
        info.points_count
    )

    if actual_count != expected_count:

        raise RuntimeError(

            "Qdrant vector count mismatch.\n"

            f"Expected: {expected_count}\n"

            f"Actual: {actual_count}"
        )

    return actual_count


# ============================================================
# DELETE COLLECTION
# ============================================================

def delete_collection(
    client,
    collection_name: str
):

    if not collection_name.startswith(
        f"{BASE_COLLECTION_NAME}_v"
    ):

        raise ValueError(
            "Refusing to delete a collection "
            "outside the versioned RAG namespace:\n"
            f"{collection_name}"
        )

    if client.collection_exists(
        collection_name=collection_name
    ):

        client.delete_collection(
            collection_name=collection_name
        )

        return True

    return False


# ============================================================
# LIST VERSIONED COLLECTIONS
# ============================================================

def list_versioned_collections(
    client
):

    collections = (
        client.get_collections()
        .collections
    )

    versions = []

    for collection in collections:

        version = get_collection_version(
            collection.name
        )

        if version is not None:

            versions.append({
                "version": version,
                "collection_name":
                    collection.name
            })

    versions.sort(
        key=lambda item:
            item["version"]
    )

    return versions


# ============================================================
# RETAIN RECENT VERSIONS
# ============================================================

def cleanup_old_versions(
    client,
    active_version: int,
    retention_count: int
):

    versions = (
        list_versioned_collections(
            client
        )
    )

    if len(versions) <= retention_count:

        return []

    # --------------------------------------------------------
    # Never delete the active version.
    # --------------------------------------------------------

    eligible = [

        item

        for item in versions

        if item["version"] != active_version

    ]

    # --------------------------------------------------------
    # Keep the newest versions first.
    # --------------------------------------------------------

    eligible.sort(
        key=lambda item:
            item["version"],
        reverse=True
    )

    keep = eligible[
        :max(
            retention_count - 1,
            0
        )
    ]

    keep_names = {
        item["collection_name"]
        for item in keep
    }

    deleted = []

    for item in versions:

        collection_name = (
            item["collection_name"]
        )

        version = item["version"]

        if version == active_version:

            continue

        if collection_name in keep_names:

            continue

        if delete_collection(
            client,
            collection_name
        ):

            deleted.append(
                collection_name
            )

    return deleted