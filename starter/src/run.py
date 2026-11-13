"""Reproducible A/B/C ingestion and evidence retrieval experiment."""
from __future__ import annotations

import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .models import DocumentPage
from .store import PgVectorStore

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_inputs() -> tuple[list[DocumentPage], list[dict]]:
    pages = [DocumentPage(**json.loads(line)) for line in
             (ROOT / "data/corpus.jsonl").read_text(encoding="utf-8").splitlines()]
    benchmark = json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))
    if len(pages) < 30 or any(len(page.text) < 1500 for page in pages):
        raise ValueError("Corpus must have 30 meaningful units of at least 1500 characters")
    if len(benchmark) < 20 or sum(q["split"] == "dev" for q in benchmark) < 15 or sum(q["split"] == "test" for q in benchmark) < 5:
        raise ValueError("Benchmark split is incomplete")
    if sum(bool(q.get("filter")) for q in benchmark) < 3 or not any(q["split"] == "test" and q.get("filter") for q in benchmark):
        raise ValueError("Not enough metadata filter questions")
    lookup = {(page.document_id, page.page): page for page in pages}
    for q in benchmark:
        page = lookup[(q["gold_source_id"], q["gold_page"])]
        if " ".join(q["evidence_quote"].split()) not in " ".join(page.text.split()):
            raise ValueError(f"Missing gold evidence for {q['id']}")
    return pages, benchmark


def main() -> None:
    load_dotenv(STARTER / ".env")
    database_url = os.getenv("DATABASE_URL", "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab")
    pages, benchmark = load_inputs()
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    embedder = MyEmbedder(MODEL)
    store = PgVectorStore(database_url, embedder.dimensions)
    store.create_schema()
    configurations = {"A": {"method": "fixed", "size": 600, "overlap": 60, "filter": False},
                      "B": {"method": "paragraph", "max_size": 650, "filter": False},
                      "C": {"method": "paragraph", "max_size": 650, "filter": True}}
    timings = {}
    b_vectors = None
    for name, config in configurations.items():
        start = time.perf_counter()
        chunks = [chunk for page in pages for chunk in (
            fixed_size(page, 600, 60) if name == "A" else by_paragraph(page, 650))]
        vectors = b_vectors if name == "C" else embedder.embed_documents([c.text for c in chunks])
        if name == "B":
            b_vectors = vectors
        store.upsert(name, chunks, vectors)
        lengths = [len(chunk.text) for chunk in chunks]
        timings[name] = {"chunk_count": len(chunks), "min_chars": min(lengths),
                         "median_chars": statistics.median(lengths), "max_chars": max(lengths),
                         "total_chars": sum(lengths), "ingest_seconds": round(time.perf_counter() - start, 3),
                         "api_cost_usd": 0}
        print(f"{name}: indexed {len(chunks)} chunks")
    traces = []
    for name, config in configurations.items():
        for question in benchmark:
            query_vector = embedder.embed_query(question["question"])
            used_filter = question.get("filter") if config["filter"] else None
            hits = store.search(name, query_vector, 3, used_filter)
            trace = evaluate_query(question, hits)
            trace["strategy"] = name
            trace["filter_applied"] = used_filter
            traces.append(trace)
    (results / "traces.jsonl").write_text(
        "".join(json.dumps(trace, ensure_ascii=False) + "\n" for trace in traces), encoding="utf-8")
    summary = {"run_at_utc": datetime.now(timezone.utc).isoformat(),
               "model": MODEL, "dimensions": embedder.dimensions,
               "store": "PostgreSQL 16 + pgvector 0.8.7, exact cosine search",
               "configurations": configurations, "resources": timings,
               "retrieval": summarize(traces)}
    (results / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["retrieval"], ensure_ascii=False))


if __name__ == "__main__":
    main()
