"""Re-run the full pipeline and persist before/after database counts."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
RESULTS = ROOT / "results"


def counts(database_url: str) -> dict[str, dict[str, int]]:
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            "SELECT strategy, COUNT(*), COUNT(DISTINCT chunk_id) FROM chunks GROUP BY strategy ORDER BY strategy"
        ).fetchall()
    return {name: {"rows": total, "distinct_chunk_ids": unique} for name, total, unique in rows}


def main() -> None:
    load_dotenv(STARTER / ".env")
    url = os.getenv("DATABASE_URL", "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab")
    before = counts(url)
    if set(before) != set("ABC"):
        raise RuntimeError("Run the pipeline once before the re-ingestion check")
    metrics_before = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))["retrieval"]
    started = datetime.now(timezone.utc).isoformat()
    process = subprocess.run([sys.executable, "-m", "src.run"], cwd=STARTER,
                             capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(f"Pipeline rerun failed: {process.stderr[-1000:]}")
    after = counts(url)
    metrics_after = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))["retrieval"]
    ok = before == after and metrics_before == metrics_after and all(
        item["rows"] == item["distinct_chunk_ids"] for item in after.values())
    evidence = {"started_at_utc": started, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "before": before, "after": after, "retrieval_unchanged": metrics_before == metrics_after,
                "no_duplicate_ids": all(item["rows"] == item["distinct_chunk_ids"] for item in after.values()),
                "passed": ok, "rerun_stdout": process.stdout.strip()}
    (RESULTS / "reingest_check.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not ok:
        raise RuntimeError("Re-ingestion changed counts or metrics; see results/reingest_check.json")
    print("Re-ingestion verified:", before, "->", after)


if __name__ == "__main__":
    main()
