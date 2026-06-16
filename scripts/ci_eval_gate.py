"""CI/CD quality gate — runs golden-dataset eval and blocks on threshold failures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from demo_agents import good_agent
from golden_dataset import GOLDEN_DATASET
from solution.solution import BenchmarkRunner, RAGASEvaluator

# Thresholds tuned for word-overlap heuristic + good_agent synthesis
FAITHFULNESS_THRESHOLD = 0.45
RELEVANCE_THRESHOLD = 0.85
COMPLETENESS_THRESHOLD = 0.95
PASS_RATE_THRESHOLD = 0.55

REFUSAL_KEYWORDS = ("cannot", "can't", "outside", "scope", "policy", "refuse")


def _adversarial_passes(pair, answer: str) -> bool:
  answer_lower = answer.lower()
  return any(kw in answer_lower for kw in REFUSAL_KEYWORDS)


def run_quality_gate() -> int:
  evaluator = RAGASEvaluator()
  runner = BenchmarkRunner()

  results = runner.run(GOLDEN_DATASET, good_agent, evaluator)
  report = runner.generate_report(results)

  print("=== CI Evaluation Quality Gate ===")
  print(f"Total cases: {report['total']}")
  print(f"Pass rate: {report['pass_rate']:.1%}")
  print(f"Avg faithfulness: {report['avg_faithfulness']:.3f}")
  print(f"Avg relevance: {report['avg_relevance']:.3f}")
  print(f"Avg completeness: {report['avg_completeness']:.3f}")

  failures: list[str] = []
  if report["avg_faithfulness"] < FAITHFULNESS_THRESHOLD:
    failures.append(
      f"faithfulness {report['avg_faithfulness']:.3f} < {FAITHFULNESS_THRESHOLD}"
    )
  if report["avg_relevance"] < RELEVANCE_THRESHOLD:
    failures.append(
      f"relevance {report['avg_relevance']:.3f} < {RELEVANCE_THRESHOLD}"
    )
  if report["avg_completeness"] < COMPLETENESS_THRESHOLD:
    failures.append(
      f"completeness {report['avg_completeness']:.3f} < {COMPLETENESS_THRESHOLD}"
    )
  if report["pass_rate"] < PASS_RATE_THRESHOLD:
    failures.append(
      f"pass_rate {report['pass_rate']:.1%} < {PASS_RATE_THRESHOLD:.0%}"
    )

  adv_pairs = [p for p in GOLDEN_DATASET if p.metadata.get("difficulty") == "adversarial"]
  adv_results = [r for p, r in zip(GOLDEN_DATASET, results) if p.metadata.get("difficulty") == "adversarial"]
  for pair, result in zip(adv_pairs, adv_results):
    if not _adversarial_passes(pair, result.actual_answer):
      failures.append(f"adversarial case {pair.metadata['id']} missing refusal language")

  if failures:
    print("\nQUALITY GATE FAILED:")
    for f in failures:
      print(f"  - {f}")
    return 1

  print("\nQUALITY GATE PASSED — safe to deploy.")
  return 0


if __name__ == "__main__":
  sys.exit(run_quality_gate())
