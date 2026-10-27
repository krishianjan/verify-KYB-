"""Embedded vector store (Chroma) — free, local, zero-server.

Two uses:
  * `business_web`  — embeddings of each business's website text, for
    cloned/templated-site detection (shell-network red flag).
  * `case_memory`   — short findings notes per business, so the LLM can recall
    prior investigation context.

Chroma's default embedding function (MiniLM, downloaded once) runs locally with
no API key. Every call is guarded: if the store or model is unavailable the
functions degrade to no-ops so the pipelines never break.
"""
from __future__ import annotations

from .config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def _collection(name: str):
    client = _get_client()
    return client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"}
    )


# --- business website embeddings -----------------------------------------

def find_similar_web(text: str, exclude_business_id: str, n: int = 5) -> list[dict]:
    """Return [{business_id, distance, metadata}] for the most similar prior sites."""
    if not settings.enable_vector or not text:
        return []
    try:
        col = _collection("business_web")
        res = col.query(query_texts=[text[:4000]], n_results=n + 1)
        ids = res.get("ids", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        out = []
        for bid, dist, meta in zip(ids, dists, metas):
            if bid == exclude_business_id:
                continue
            out.append({"business_id": bid, "distance": float(dist),
                        "metadata": meta or {}})
        return out[:n]
    except Exception:  # noqa: BLE001
        return []


def upsert_web(business_id: str, text: str, metadata: dict | None = None) -> None:
    if not settings.enable_vector or not text:
        return
    try:
        col = _collection("business_web")
        col.upsert(
            ids=[business_id],
            documents=[text[:4000]],
            metadatas=[metadata or {}],
        )
    except Exception:  # noqa: BLE001
        pass


# --- case memory ----------------------------------------------------------

def add_memory(business_id: str, note: str) -> None:
    if not settings.enable_vector or not note:
        return
    try:
        col = _collection("case_memory")
        import hashlib

        mid = hashlib.sha1(f"{business_id}:{note}".encode()).hexdigest()[:16]
        col.upsert(ids=[mid], documents=[note], metadatas=[{"business_id": business_id}])
    except Exception:  # noqa: BLE001
        pass


def recall_memory(business_id: str, query: str = "", n: int = 5) -> list[str]:
    if not settings.enable_vector:
        return []
    try:
        col = _collection("case_memory")
        if query:
            res = col.query(
                query_texts=[query], n_results=n,
                where={"business_id": business_id},
            )
            return res.get("documents", [[]])[0]
        res = col.get(where={"business_id": business_id}, limit=n)
        return res.get("documents", [])
    except Exception:  # noqa: BLE001
        return []
