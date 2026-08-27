import json
import os
import shutil
from pathlib import Path

from sentence_transformers import SentenceTransformer

from ingestion.chunker import parse_markdown

from ingestion.embedder import (
    build_embedding_text,
    MODEL_NAME,
)

from ingestion.manifest import (
    DOCUMENT_FILE,
    calculate_sha256,
    load_manifest,
    save_manifest,
    get_next_index_version,
    get_document_version,
    build_collection_name,
    get_retention_count,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
)

from vector_store.vector_store import (
    create_qdrant_client,
    create_points,
    create_collection,
    insert_points,
    verify_collection,
    cleanup_old_versions,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = (
    Path(__file__).resolve().parent.parent
)

CHUNKS_FILE = (
    BASE_DIR
    / "data"
    / "chunks.json"
)

EMBEDDED_FILE = (
    BASE_DIR
    / "data"
    / "embedded_chunks.json"
)

TEMP_CHUNKS_FILE = (
    BASE_DIR
    / "data"
    / ".chunks.tmp.json"
)

TEMP_EMBEDDED_FILE = (
    BASE_DIR
    / "data"
    / ".embedded_chunks.tmp.json"
)


# ============================================================
# JSON
# ============================================================

def write_json_atomic(
    file_path: Path,
    data
):
    """
    Write JSON safely.

    Data is first written to a temporary file,
    flushed to disk, and then atomically replaced.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_file = file_path.with_suffix(
        file_path.suffix + ".write.tmp"
    )

    try:

        with temp_file.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )

            file.flush()

            os.fsync(
                file.fileno()
            )

        temp_file.replace(
            file_path
        )

    finally:

        if temp_file.exists():

            try:
                temp_file.unlink()

            except OSError:

                pass


# ============================================================
# CHUNK DOCUMENT
# ============================================================

def build_chunks():

    print(
        "\n[1/4] Chunking document..."
    )

    headings, chunks = (
        parse_markdown(
            DOCUMENT_FILE
        )
    )

    if not chunks:

        raise RuntimeError(
            "Document produced zero chunks."
        )

    write_json_atomic(
        TEMP_CHUNKS_FILE,
        chunks
    )

    print(
        f"Detected headings: "
        f"{len(headings)}"
    )

    print(
        f"Created chunks: "
        f"{len(chunks)}"
    )

    return chunks


# ============================================================
# BUILD EMBEDDINGS
# ============================================================

def build_embeddings(
    chunks
):

    print(
        "\n[2/4] Loading embedding model..."
    )

    print(
        f"Model: {MODEL_NAME}"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    texts = [
        build_embedding_text(
            chunk
        )
        for chunk in chunks
    ]

    if not texts:

        raise RuntimeError(
            "No texts available for embedding."
        )

    print(
        f"Generating {len(texts)} embeddings..."
    )

    embeddings = model.encode(

        texts,

        normalize_embeddings=True,

        show_progress_bar=True
    )

    # --------------------------------------------------------
    # Validate embedding count.
    # --------------------------------------------------------

    if len(embeddings) != len(chunks):

        raise RuntimeError(

            "Embedding count does not "
            "match chunk count.\n"

            f"Chunks: {len(chunks)}\n"

            f"Embeddings: {len(embeddings)}"
        )

    # --------------------------------------------------------
    # Validate embedding dimension.
    # --------------------------------------------------------

    actual_dimension = (
        embeddings.shape[1]
    )

    if actual_dimension != (
        EMBEDDING_DIMENSION
    ):

        raise RuntimeError(

            "Embedding dimension mismatch.\n"

            f"Expected: {EMBEDDING_DIMENSION}\n"

            f"Received: {actual_dimension}"
        )

    embedded_chunks = []

    for (
        chunk,
        text,
        embedding
    ) in zip(
        chunks,
        texts,
        embeddings
    ):

        embedded_chunk = (
            chunk.copy()
        )

        embedded_chunk["text"] = text

        embedded_chunk["embedding"] = (
            embedding.tolist()
        )

        embedded_chunks.append(
            embedded_chunk
        )

    write_json_atomic(
        TEMP_EMBEDDED_FILE,
        embedded_chunks
    )

    print(
        f"Generated {len(embedded_chunks)} "
        "embeddings."
    )

    print(
        f"Embedding dimension: "
        f"{actual_dimension}"
    )

    return embedded_chunks


# ============================================================
# BUILD VERSIONED QDRANT INDEX
# ============================================================

def build_qdrant_index(
    embedded_chunks,
    index_version
):

    collection_name = (
        build_collection_name(
            index_version
        )
    )

    print(
        "\n[3/4] Building new Qdrant index..."
    )

    print(
        f"New collection: "
        f"{collection_name}"
    )

    client = create_qdrant_client()

    try:

        # ----------------------------------------------------
        # NEVER overwrite an existing version.
        # ----------------------------------------------------

        if client.collection_exists(
            collection_name=collection_name
        ):

            raise RuntimeError(

                f"Collection already exists:\n"
                f"{collection_name}\n\n"

                "Refusing to overwrite an "
                "existing index version."
            )

        # ----------------------------------------------------
        # Create new collection.
        # ----------------------------------------------------

        create_collection(
            client,
            collection_name
        )

        # ----------------------------------------------------
        # Create points.
        # ----------------------------------------------------

        points = create_points(
            embedded_chunks
        )

        if not points:

            raise RuntimeError(
                "No Qdrant points were generated."
            )

        # ----------------------------------------------------
        # Upload.
        # ----------------------------------------------------

        print(
            f"Uploading {len(points)} vectors..."
        )

        insert_points(

            client,

            collection_name,

            points
        )

        # ----------------------------------------------------
        # Validate.
        # ----------------------------------------------------

        stored_count = (
            verify_collection(

                client,

                collection_name,

                len(points)
            )
        )

        print(
            f"Qdrant validation passed: "
            f"{stored_count} vectors."
        )

        return collection_name

    except Exception:

        # ----------------------------------------------------
        # Delete ONLY the newly-created failed collection.
        #
        # The previous active collection is never touched.
        # ----------------------------------------------------

        try:

            if client.collection_exists(
                collection_name=collection_name
            ):

                client.delete_collection(
                    collection_name=collection_name
                )

        except Exception as cleanup_error:

            print(
                "\nWARNING: Could not clean up "
                "failed collection."
            )

            print(
                cleanup_error
            )

        raise

    finally:

        client.close()


# ============================================================
# ACTIVE INDEX VALIDATION
# ============================================================

def active_index_is_valid(
    manifest
):

    if not manifest:

        return False

    if manifest.get(
        "status"
    ) != "ready":

        return False

    collection_name = (
        manifest.get(
            "collection_name"
        )
    )

    if not collection_name:

        return False

    client = create_qdrant_client()

    try:

        # ----------------------------------------------------
        # Collection must exist.
        # ----------------------------------------------------

        if not client.collection_exists(
            collection_name=collection_name
        ):

            print(
                "\nWARNING: Active Qdrant "
                "collection is missing:"
            )

            print(
                collection_name
            )

            return False

        # ----------------------------------------------------
        # Collection must contain vectors.
        # ----------------------------------------------------

        info = client.get_collection(
            collection_name=collection_name
        )

        if not info.points_count:

            print(
                "\nWARNING: Active Qdrant "
                "collection contains zero vectors:"
            )

            print(
                collection_name
            )

            return False

        return True

    except Exception as error:

        print(
            "\nWARNING: Could not validate "
            "active Qdrant collection."
        )

        print(error)

        return False

    finally:

        client.close()


# ============================================================
# INDEX CONFIGURATION CHECK
# ============================================================

def index_configuration_changed(
    manifest
):

    if not manifest:

        return True

    stored_model = (
        manifest.get(
            "embedding_model"
        )
    )

    stored_dimension = (
        manifest.get(
            "embedding_dimension"
        )
    )

    if stored_model != EMBEDDING_MODEL:

        print(
            "\nEmbedding model changed."
        )

        print(
            f"Previous: {stored_model}"
        )

        print(
            f"Current:  {EMBEDDING_MODEL}"
        )

        return True

    if stored_dimension != (
        EMBEDDING_DIMENSION
    ):

        print(
            "\nEmbedding dimension changed."
        )

        print(
            f"Previous: {stored_dimension}"
        )

        print(
            f"Current:  {EMBEDDING_DIMENSION}"
        )

        return True

    return False


# ============================================================
# PROMOTE GENERATED FILES
# ============================================================

def promote_generated_files():

    if not TEMP_CHUNKS_FILE.exists():

        raise RuntimeError(
            "Temporary chunks file missing."
        )

    if not TEMP_EMBEDDED_FILE.exists():

        raise RuntimeError(
            "Temporary embeddings file missing."
        )

    # --------------------------------------------------------
    # Replace generated artifacts atomically.
    # --------------------------------------------------------

    os.replace(
        TEMP_CHUNKS_FILE,
        CHUNKS_FILE
    )

    os.replace(
        TEMP_EMBEDDED_FILE,
        EMBEDDED_FILE
    )


# ============================================================
# CLEANUP TEMPORARY FILES
# ============================================================

def cleanup_temp_files():

    temporary_files = (
        TEMP_CHUNKS_FILE,
        TEMP_EMBEDDED_FILE
    )

    for file_path in temporary_files:

        if file_path.exists():

            try:

                file_path.unlink()

            except OSError as error:

                print(
                    f"WARNING: Could not remove "
                    f"temporary file {file_path}: "
                    f"{error}"
                )


# ============================================================
# CLEANUP OLD INDEXES
# ============================================================

def cleanup_old_indexes(
    active_version
):

    print(
        "\nCleaning up old index versions..."
    )

    client = create_qdrant_client()

    try:

        deleted_collections = (
            cleanup_old_versions(

                client,

                active_version=
                    active_version,

                retention_count=
                    get_retention_count()
            )
        )

        if deleted_collections:

            print(
                "Deleted old collections:"
            )

            for collection_name in (
                deleted_collections
            ):

                print(
                    f"  - {collection_name}"
                )

        else:

            print(
                "No old collections "
                "required cleanup."
            )

    except Exception as error:

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Cleanup is maintenance.
        # It must NEVER invalidate a successfully
        # activated index.
        # ----------------------------------------------------

        print(
            "\nWARNING: Old index cleanup failed."
        )

        print(error)

        print(
            "The active index remains valid."
        )

    finally:

        client.close()


# ============================================================
# SYNCHRONIZE
# ============================================================

def synchronize():

    print("=" * 70)
    print("PRODUCTION RAG DOCUMENT SYNC")
    print("=" * 70)

    print(
        f"\nDocument:\n"
        f"{DOCUMENT_FILE}"
    )

    # --------------------------------------------------------
    # Verify source document.
    # --------------------------------------------------------

    if not DOCUMENT_FILE.exists():

        raise FileNotFoundError(
            f"Document not found:\n"
            f"{DOCUMENT_FILE}"
        )

    # --------------------------------------------------------
    # Calculate document fingerprint.
    # --------------------------------------------------------

    current_hash = (
        calculate_sha256(
            DOCUMENT_FILE
        )
    )

    print(
        f"\nCurrent SHA-256:\n"
        f"{current_hash}"
    )

    # --------------------------------------------------------
    # Load previous manifest.
    # --------------------------------------------------------

    previous_manifest = (
        load_manifest()
    )

    # ========================================================
    # FIRST INDEX
    # ========================================================

    if not previous_manifest:

        print()
        print("=" * 70)
        print("FIRST DOCUMENT INDEX")
        print("=" * 70)

        document_version = 1

        index_version = 1

    # ========================================================
    # EXISTING INDEX
    # ========================================================

    else:

        previous_hash = (
            previous_manifest.get(
                "document_sha256"
            )
        )

        active_collection = (
            previous_manifest.get(
                "collection_name"
            )
        )

        current_document_version = (
            previous_manifest.get(
                "document_version",
                0
            )
        )

        current_index_version = (
            previous_manifest.get(
                "index_version",
                0
            )
        )

        print(
            f"\nStored SHA-256:\n"
            f"{previous_hash}"
        )

        print(
            f"Active collection: "
            f"{active_collection}"
        )

        print(
            f"Document version: "
            f"{current_document_version}"
        )

        print(
            f"Index version: "
            f"{current_index_version}"
        )

        # ----------------------------------------------------
        # Determine whether rebuild is necessary.
        # ----------------------------------------------------

        document_changed = (
            current_hash != previous_hash
        )

        configuration_changed = (
            index_configuration_changed(
                previous_manifest
            )
        )

        active_index_valid = (
            active_index_is_valid(
                previous_manifest
            )
        )

        # ----------------------------------------------------
        # Nothing changed and active index is healthy.
        # ----------------------------------------------------

        if (
            not document_changed
            and not configuration_changed
            and active_index_valid
        ):

            print()
            print("=" * 70)
            print("DOCUMENT AND INDEX UNCHANGED")
            print("=" * 70)

            print(
                "\nNo re-indexing required."
            )

            print(
                f"Active collection: "
                f"{active_collection}"
            )

            print(
                f"Version: "
                f"{current_index_version}"
            )

            return False

        # ----------------------------------------------------
        # Document unchanged but index/configuration broken.
        # ----------------------------------------------------

        if (
            not document_changed
            and not configuration_changed
            and not active_index_valid
        ):

            print()
            print("=" * 70)
            print("ACTIVE INDEX INVALID")
            print("=" * 70)

            print(
                "\nThe document has not changed, "
                "but the active Qdrant index is "
                "missing or invalid."
            )

            print(
                "A new index will be built."
            )

        # ----------------------------------------------------
        # Document changed.
        # ----------------------------------------------------

        elif document_changed:

            print()
            print("=" * 70)
            print("DOCUMENT CHANGED")
            print("=" * 70)

        # ----------------------------------------------------
        # Embedding configuration changed.
        # ----------------------------------------------------

        elif configuration_changed:

            print()
            print("=" * 70)
            print("INDEX CONFIGURATION CHANGED")
            print("=" * 70)

        document_version = (
            get_document_version(

                previous_manifest,

                current_hash
            )
        )

        index_version = (
            get_next_index_version(
                previous_manifest
            )
        )

    # ========================================================
    # NEW INDEX INFORMATION
    # ========================================================

    collection_name = (
        build_collection_name(
            index_version
        )
    )

    print(
        f"\nDocument version: "
        f"{document_version}"
    )

    print(
        f"Index version: "
        f"{index_version}"
    )

    print(
        f"New collection: "
        f"{collection_name}"
    )

    # ========================================================
    # BUILD
    # ========================================================

    try:

        # ----------------------------------------------------
        # 1. Chunk.
        # ----------------------------------------------------

        chunks = build_chunks()

        # ----------------------------------------------------
        # 2. Embed.
        # ----------------------------------------------------

        embedded_chunks = (
            build_embeddings(
                chunks
            )
        )

        # ----------------------------------------------------
        # 3. Build + validate new Qdrant index.
        # ----------------------------------------------------

        built_collection = (
            build_qdrant_index(

                embedded_chunks,

                index_version
            )
        )

        # ----------------------------------------------------
        # 4. Finalize local artifacts.
        # ----------------------------------------------------

        print(
            "\n[4/4] Finalizing..."
        )

        promote_generated_files()

        # ----------------------------------------------------
        # Activate new version.
        #
        # Manifest is the source of truth for which
        # collection is currently active.
        # ----------------------------------------------------

        save_manifest(

            document=DOCUMENT_FILE,

            document_hash=current_hash,

            document_version=document_version,

            index_version=index_version,

            collection_name=built_collection,

            chunk_count=len(
                embedded_chunks
            )
        )

        # ----------------------------------------------------
        # Success.
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("RAG INDEX ACTIVATED")
        print("=" * 70)

        print(
            f"\nDocument version: "
            f"{document_version}"
        )

        print(
            f"Index version: "
            f"{index_version}"
        )

        print(
            f"Active collection: "
            f"{built_collection}"
        )

        print(
            f"Chunks: "
            f"{len(embedded_chunks)}"
        )

        # ----------------------------------------------------
        # Cleanup old versions AFTER activation.
        # ----------------------------------------------------

        cleanup_old_indexes(
            index_version
        )

        print()
        print(
            "Previous retained indexes remain "
            "available for rollback."
        )

        return True

    except Exception:

        cleanup_temp_files()

        print()
        print("=" * 70)
        print("RAG INDEX UPDATE FAILED")
        print("=" * 70)

        print(
            "\nThe previous active index "
            "has NOT been intentionally replaced."
        )

        print(
            "Any newly-created failed index "
            "was cleaned up when possible."
        )

        raise


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        synchronize()

    except Exception as error:

        print()
        print(
            f"ERROR: {error}"
        )

        raise SystemExit(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()