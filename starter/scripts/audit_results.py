"""Record a fixed qualitative sample and validate trace metadata against source units."""
import json
from pathlib import Path

from src.chunking import by_paragraph, fixed_size
from src.models import DocumentPage

ROOT = Path(__file__).resolve().parents[2]
pages = [DocumentPage(**json.loads(line)) for line in (ROOT / "data/corpus.jsonl").read_text(encoding="utf-8").splitlines()]
traces = [json.loads(line) for line in (ROOT / "results/traces.jsonl").read_text(encoding="utf-8").splitlines()]

# Ten source positions chosen evenly by ordered page ID, before reviewing scores.
# Scores use the 0/1/2 rubric in GUIDE.md. C has the same chunks as B.
COHERENCE = {
    "A": [0, 0, 0, 0, 1, 1, 0, 1, 1, 0],
    "B": [2, 2, 1, 1, 1, 1, 2, 1, 1, 1],
    "C": [2, 2, 1, 1, 1, 1, 2, 1, 1, 1],
}
GROUNDING = {
    "A": [0, 0, 0, 0, 0, 1],
    "B": [0, 0, 0, 0, 0, 1],
    "C": [0, 0, 0, 2, 0, 1],
}
COHERENCE_REASONS = {
    "A": [
        "Starts mid-sentence and ends before the explanation finishes.",
        "Cuts the indentation explanation before its condition is complete.",
        "Starts in the previous idea and ends mid-sentence.",
        "Both boundaries cut the argument-list explanation.",
        "The example is partly readable but its setup is missing.",
        "The module example is readable but starts without its definition.",
        "Both boundaries cut the package-import explanation.",
        "The table example is partly readable; its code is cut.",
        "The exception-argument idea is partly understandable amid adjacent text.",
        "Starts and ends inside an exception example.",
    ],
    "B": [
        "Has a section heading, explanation and complete calculator example.",
        "The indentation explanation stays in one readable paragraph.",
        "Main local-scope idea is present, but the last clause is cut.",
        "Adjacent argument cases remain understandable but lack a heading.",
        "Example is readable but section context is missing.",
        "Module code and use are visible, but introductory context is missing.",
        "Package import rule and consequence are self-contained.",
        "Output example is readable but its setup is partly outside the chunk.",
        "Exception arguments are explained without full surrounding context.",
        "Example is readable but the surrounding exception-group context is thin.",
    ],
}
COHERENCE_REASONS["C"] = COHERENCE_REASONS["B"]
TEST_IDS = [f"q{i:02}" for i in range(19, 25)]


def main() -> None:
    lookup = {(p.document_id, p.page): p for p in pages}
    indices = [round(i * (len(pages) - 1) / 9) for i in range(10)]
    samples = []
    for j, index in enumerate(indices):
        page = pages[index]
        blocks = [block for block in page.text.split("\n\n") if len(block) > 100]
        anchor = blocks[len(blocks) // 2][:30]
        row = {"source_id": page.document_id, "page": page.page, "anchor": anchor, "strategies": {}}
        for strategy in "ABC":
            chunks = fixed_size(page, 600, 60) if strategy == "A" else by_paragraph(page, 650)
            match = next((chunk for chunk in chunks if anchor in chunk.text), None)
            if match is None:
                raise ValueError(f"Cannot locate coherence anchor {page.document_id}:{page.page}")
            row["strategies"][strategy] = {"chunk_id": match.chunk_id, "text": match.text,
                                            "score": COHERENCE[strategy][j],
                                            "reason": COHERENCE_REASONS[strategy][j]}
        samples.append(row)
    metadata = {}
    grounding = {}
    for strategy in "ABC":
        subset = [trace for trace in traces if trace["strategy"] == strategy and trace["split"] == "test"]
        if [trace["id"] for trace in subset] != TEST_IDS:
            raise ValueError("Unexpected test trace order")
        checked = 0
        correct = 0
        for trace in subset:
            for hit in trace["hits"]:
                checked += 1
                page = lookup.get((hit["document_id"], hit["page"]))
                if (page and hit["source"] == page.source and
                    hit["metadata"].get("chapter") == page.metadata["chapter"] and
                    hit["text"] in page.text):
                    correct += 1
        filtered = [trace for trace in subset if trace["filter_applied"]]
        compliant = sum(all(hit["metadata"].get("chapter") == trace["filter_applied"]["chapter"]
                            for hit in trace["hits"]) for trace in filtered)
        metadata[strategy] = {"correct": correct, "checked": checked,
                              "filter_compliant": compliant, "filter_questions": len(filtered)}
        grounding[strategy] = {"labels": dict(zip(TEST_IDS, GROUNDING[strategy])),
                               "counts": {str(n): GROUNDING[strategy].count(n) for n in range(3)},
                               "mean_out_of_2": sum(GROUNDING[strategy]) / len(TEST_IDS)}
    audit = {"coherence_selection": "10 evenly spaced page IDs in corpus order; middle text block per page",
             "coherence_samples": samples,
             "coherence_mean_out_of_2": {name: sum(values) / len(values) for name, values in COHERENCE.items()},
             "metadata": metadata, "grounding": grounding,
             "grounding_notes": {
                 "q19-q21": "Retrieved excerpts do not contain the required JSON/zfill/error-type evidence.",
                 "q22": "Only C retrieves the sufficient except-class statement; its chapter filter excludes wrong chapters.",
                 "q23": "Top-3 does not state that finally executes in every event.",
                 "q24": "Top-3 discusses or demonstrates ExceptionGroup but lacks the full defining statement in one clear excerpt."}}
    (ROOT / "results/audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved audit:", audit["coherence_mean_out_of_2"], metadata, grounding)


if __name__ == "__main__":
    main()
