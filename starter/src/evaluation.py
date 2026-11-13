"""Evidence based retrieval metrics and traces; human labels stay separate."""
from typing import Any
from .ingestion import normalize_text


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    gold = question.get("gold", [{"source_id": question["gold_source_id"],
                                   "page": question["gold_page"],
                                   "evidence_quote": question["evidence_quote"]}])
    annotated = []
    for hit in hits:
        matched = any(hit["document_id"] == item["source_id"] and
                      hit["page"] == item["page"] and
                      " ".join(normalize_text(item["evidence_quote"]).casefold().split()) in
                      " ".join(normalize_text(hit["text"]).casefold().split()) for item in gold)
        annotated.append({**hit, "evidence_hit": matched})
    return {"id": question["id"], "split": question["split"],
            "question": question["question"], "filter": question.get("filter"),
            "gold": gold, "hit1": bool(annotated and annotated[0]["evidence_hit"]),
            "hit3": any(hit["evidence_hit"] for hit in annotated), "hits": annotated}


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for strategy in sorted({trace["strategy"] for trace in traces}):
        result[strategy] = {}
        for split in ("dev", "test"):
            subset = [trace for trace in traces if trace["strategy"] == strategy and trace["split"] == split]
            result[strategy][split] = {"n": len(subset),
                                       "hit1": sum(t["hit1"] for t in subset),
                                       "hit3": sum(t["hit3"] for t in subset)}
    return result
