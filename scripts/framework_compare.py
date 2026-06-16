"""Compare RAGAS heuristic vs N-gram evaluator on the golden dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from demo_agents import mock_rag_agent
from golden_dataset import GOLDEN_DATASET
from solution.solution import NgramEvaluator, RAGASEvaluator


def compare_frameworks(agent_fn=mock_rag_agent) -> dict:
  ragas = RAGASEvaluator()
  ngram = NgramEvaluator()
  rows: list[dict] = []

  for pair in GOLDEN_DATASET:
    answer = agent_fn(pair.question)
    r = ragas.run_full_eval(answer, pair.question, pair.context, pair.expected_answer)
    n = ngram.run_full_eval(answer, pair.question, pair.context, pair.expected_answer)
    rows.append({
      "id": pair.metadata["id"],
      "question": pair.question[:50],
      "ragas_faithfulness": round(r.faithfulness, 3),
      "ngram_faithfulness": round(n["faithfulness"], 3),
      "ragas_relevance": round(r.relevance, 3),
      "ngram_relevance": round(n["relevance"], 3),
      "ragas_completeness": round(r.completeness, 3),
      "ngram_completeness": round(n["completeness"], 3),
      "ragas_overall": round(r.overall_score(), 3),
      "ngram_overall": round(
        (n["faithfulness"] + n["relevance"] + n["completeness"]) / 3, 3
      ),
    })

  def _avg(key: str) -> float:
    return sum(row[key] for row in rows) / len(rows)

  summary = {
    "frameworks": ["RAGAS Heuristic (word overlap)", "NgramEvaluator (bigram overlap)"],
    "per_pair": rows,
    "averages": {
      "ragas": {
        "faithfulness": round(_avg("ragas_faithfulness"), 3),
        "relevance": round(_avg("ragas_relevance"), 3),
        "completeness": round(_avg("ragas_completeness"), 3),
        "overall": round(_avg("ragas_overall"), 3),
      },
      "ngram": {
        "faithfulness": round(_avg("ngram_faithfulness"), 3),
        "relevance": round(_avg("ngram_relevance"), 3),
        "completeness": round(_avg("ngram_completeness"), 3),
        "overall": round(_avg("ngram_overall"), 3),
      },
    },
    "insight": (
      "N-gram overlap is stricter on phrase structure; word overlap is more lenient "
      "on paraphrases but can miss semantic errors both frameworks agree on."
    ),
  }
  return summary


def main() -> None:
  result = compare_frameworks()
  print(json.dumps(result, indent=2))


if __name__ == "__main__":
  main()
