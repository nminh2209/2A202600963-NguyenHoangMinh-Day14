"""
Day 14 — AI Evaluation & Benchmarking Pipeline
AICB-P1: AI Practical Competency Program, Phase 1
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Task 1 — Data Models (Golden Dataset + Evaluation Results)
# ---------------------------------------------------------------------------

@dataclass
class QAPair:
  question: str
  expected_answer: str
  context: str = ""
  metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
  qa_pair: QAPair
  actual_answer: str
  faithfulness: float
  relevance: float
  completeness: float
  passed: bool
  failure_type: str | None = None

  def overall_score(self) -> float:
    return (self.faithfulness + self.relevance + self.completeness) / 3.0


# ---------------------------------------------------------------------------
# Task 2 — RAGAS Evaluator (Simplified word-overlap heuristic)
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset({
  "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
  "is", "it", "of", "on", "or", "that", "the", "to", "was", "were", "with",
})


def _tokenize(text: str) -> set[str]:
  """Lowercase word tokenization, ignoring punctuation and stopwords."""
  if not text:
    return set()
  return {
    token for token in re.findall(r"\b\w+\b", text.lower())
    if token not in _STOPWORDS
  }


def _clamp(value: float) -> float:
  return max(0.0, min(1.0, value))


class RAGASEvaluator:
  """Evaluates RAG pipeline outputs using RAGAS-inspired heuristics."""

  def evaluate_faithfulness(self, answer: str, context: str) -> float:
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
      return 1.0
    context_tokens = _tokenize(context or "")
    if not context_tokens:
      return 0.0
    overlap = len(answer_tokens & context_tokens)
    return _clamp(overlap / len(answer_tokens))

  def evaluate_relevance(self, answer: str, question: str) -> float:
    question_tokens = _tokenize(question)
    if not question_tokens:
      return 1.0
    answer_tokens = _tokenize(answer)
    overlap = len(answer_tokens & question_tokens)
    return _clamp(overlap / len(question_tokens))

  def evaluate_completeness(self, answer: str, expected: str) -> float:
    expected_tokens = _tokenize(expected)
    if not expected_tokens:
      return 1.0
    answer_tokens = _tokenize(answer)
    overlap = len(answer_tokens & expected_tokens)
    return _clamp(overlap / len(expected_tokens))

  def evaluate_context_utilization(self, answer: str, context: str) -> float:
    """Custom metric: how much of the retrieved context appears in the answer.

    Unlike faithfulness (answer grounded in context), this measures whether
    the agent actually used the retrieved material vs ignoring it.
    """
    context_tokens = _tokenize(context or "")
    if not context_tokens:
      return 1.0
    answer_tokens = _tokenize(answer)
    overlap = len(answer_tokens & context_tokens)
    return _clamp(overlap / len(context_tokens))

  def run_full_eval(
    self,
    answer: str,
    question: str,
    context: str,
    expected: str,
  ) -> EvalResult:
    faithfulness = self.evaluate_faithfulness(answer, context or "")
    relevance = self.evaluate_relevance(answer, question)
    completeness = self.evaluate_completeness(answer, expected)
    passed = faithfulness >= 0.5 and relevance >= 0.5 and completeness >= 0.5

    failure_type: str | None = None
    if not passed:
      if faithfulness < 0.3:
        failure_type = "hallucination"
      elif relevance < 0.3:
        failure_type = "irrelevant"
      elif completeness < 0.3:
        failure_type = "incomplete"
      else:
        failure_type = "off_topic"

    return EvalResult(
      qa_pair=QAPair(question=question, expected_answer=expected, context=context or ""),
      actual_answer=answer,
      faithfulness=faithfulness,
      relevance=relevance,
      completeness=completeness,
      passed=passed,
      failure_type=failure_type,
    )


# ---------------------------------------------------------------------------
# Task 3 — LLM Judge
# ---------------------------------------------------------------------------

class LLMJudge:
  """Uses an LLM to score AI responses according to a rubric."""

  def __init__(self, judge_llm_fn: Callable[[str], str]) -> None:
    self.judge_llm_fn = judge_llm_fn

  def score_response(
    self,
    question: str,
    answer: str,
    rubric: dict[str, Any],
  ) -> dict[str, Any]:
    rubric_lines = "\n".join(f"- {name}: {desc}" for name, desc in rubric.items())
    prompt = (
      "You are an expert judge evaluating an AI assistant response.\n\n"
      f"Question:\n{question}\n\n"
      f"Answer:\n{answer}\n\n"
      f"Rubric:\n{rubric_lines}\n\n"
      "Return JSON mapping each criterion to a score between 0.0 and 1.0.\n"
      'Example: {"accuracy": 0.8, "clarity": 0.7}'
    )
    raw = self.judge_llm_fn(prompt)

    scores: dict[str, float] = {}
    try:
      parsed = json.loads(raw)
      if isinstance(parsed, dict):
        for key in rubric:
          if key in parsed:
            scores[key] = float(parsed[key])
    except (json.JSONDecodeError, TypeError, ValueError):
      pass

    if not scores:
      scores = {key: 0.5 for key in rubric}

    return {"scores": scores, "reasoning": raw}

  def detect_bias(self, scores_batch: list[dict[str, Any]]) -> dict[str, Any]:
    all_scores: list[float] = []
    for entry in scores_batch:
      criterion_scores = entry.get("scores", {})
      all_scores.extend(float(v) for v in criterion_scores.values())

    avg_all = sum(all_scores) / len(all_scores) if all_scores else 0.0
    leniency_bias = avg_all > 0.8
    severity_bias = avg_all < 0.3

    positional_bias = False
    if len(scores_batch) >= 2:
      def _entry_avg(entry: dict[str, Any]) -> float:
        values = [float(v) for v in entry.get("scores", {}).values()]
        return sum(values) / len(values) if values else 0.0

      first_avg = _entry_avg(scores_batch[0])
      rest_avgs = [_entry_avg(entry) for entry in scores_batch[1:]]
      positional_bias = all(first_avg > avg for avg in rest_avgs)

    return {
      "positional_bias": positional_bias,
      "leniency_bias": leniency_bias,
      "severity_bias": severity_bias,
    }


# ---------------------------------------------------------------------------
# Task 4 — Benchmark Runner
# ---------------------------------------------------------------------------

class BenchmarkRunner:
  """Runs a full evaluation benchmark."""

  def run(
    self,
    qa_pairs: list[QAPair],
    agent_fn: Callable[[str], str],
    evaluator: RAGASEvaluator,
  ) -> list[EvalResult]:
    results: list[EvalResult] = []
    for pair in qa_pairs:
      actual_answer = agent_fn(pair.question)
      result = evaluator.run_full_eval(
        answer=actual_answer,
        question=pair.question,
        context=pair.context or "",
        expected=pair.expected_answer,
      )
      result.qa_pair = pair
      results.append(result)
    return results

  def generate_report(self, results: list[EvalResult]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
      return {
        "total": 0,
        "passed": 0,
        "pass_rate": 0.0,
        "avg_faithfulness": 0.0,
        "avg_relevance": 0.0,
        "avg_completeness": 0.0,
        "failure_types": {},
      }

    passed = sum(1 for r in results if r.passed)
    failure_types: dict[str, int] = {}
    for r in results:
      if r.failure_type:
        failure_types[r.failure_type] = failure_types.get(r.failure_type, 0) + 1

    return {
      "total": total,
      "passed": passed,
      "pass_rate": passed / total,
      "avg_faithfulness": sum(r.faithfulness for r in results) / total,
      "avg_relevance": sum(r.relevance for r in results) / total,
      "avg_completeness": sum(r.completeness for r in results) / total,
      "failure_types": failure_types,
    }

  def run_regression(self, new_results: list, baseline_results: list) -> dict:
    def _avg_metric(results: list, metric: str) -> float:
      if not results:
        return 0.0
      return sum(getattr(r, metric) for r in results) / len(results)

    metrics = ("faithfulness", "relevance", "completeness")
    new_avgs = {m: _avg_metric(new_results, m) for m in metrics}
    baseline_avgs = {m: _avg_metric(baseline_results, m) for m in metrics}

    regressions: list[str] = []
    for metric in metrics:
      if baseline_avgs[metric] - new_avgs[metric] > 0.05:
        regressions.append(metric)

    return {
      "new_avg_faithfulness": new_avgs["faithfulness"],
      "new_avg_relevance": new_avgs["relevance"],
      "new_avg_completeness": new_avgs["completeness"],
      "baseline_avg_faithfulness": baseline_avgs["faithfulness"],
      "baseline_avg_relevance": baseline_avgs["relevance"],
      "baseline_avg_completeness": baseline_avgs["completeness"],
      "regressions": regressions,
      "passed": len(regressions) == 0,
    }

  def identify_failures(
    self,
    results: list[EvalResult],
    threshold: float = 0.5,
  ) -> list[EvalResult]:
    return [
      r for r in results
      if r.faithfulness < threshold
      or r.relevance < threshold
      or r.completeness < threshold
    ]


# ---------------------------------------------------------------------------
# Task 5 — Failure Analyzer
# ---------------------------------------------------------------------------

class FailureAnalyzer:
  """Analyzes failed evaluation results to identify patterns and suggest fixes."""

  def categorize_failures(self, failures: list[EvalResult]) -> dict[str, int]:
    categories: dict[str, int] = {}
    for failure in failures:
      if failure.failure_type:
        key = failure.failure_type
        categories[key] = categories.get(key, 0) + 1
    return categories

  def find_root_cause(self, failure: EvalResult) -> str:
    scores = {
      "faithfulness": failure.faithfulness,
      "relevance": failure.relevance,
      "completeness": failure.completeness,
    }
    min_score = min(scores.values())
    lowest = [name for name, value in scores.items() if value == min_score]
    if len(lowest) > 1:
      return "Multiple issues detected — review full pipeline"
    if lowest[0] == "faithfulness":
      return "Context is missing or irrelevant — improve retrieval"
    if lowest[0] == "relevance":
      return "Answer does not address the question — improve prompt clarity"
    return "Answer is missing key information — increase context window or improve generation"

  def generate_improvement_log(self, failures: list, suggestions: list[str]) -> str:
    header = (
      "| Failure ID | Type | Root Cause | Suggested Fix | Status |\n"
      "|------------|------|------------|---------------|--------|"
    )
    rows: list[str] = []
    for idx, failure in enumerate(failures, start=1):
      failure_id = f"F{idx:03d}"
      failure_type = failure.failure_type or "unknown"
      root_cause = self.find_root_cause(failure)
      suggestion = suggestions[idx - 1] if idx - 1 < len(suggestions) else "Review pipeline"
      rows.append(
        f"| {failure_id} | {failure_type} | {root_cause} | {suggestion} | Open |"
      )
    return header + ("\n" + "\n".join(rows) if rows else "")

  def generate_improvement_suggestions(self, failures: list[EvalResult]) -> list[str]:
    if not failures:
      return []

    categories = self.categorize_failures(failures)
    suggestions: list[str] = []

    if categories.get("hallucination", 0) > 0:
      suggestions.append(
        "Implement hallucination checker to filter unsupported claims before returning answers"
      )
    if categories.get("irrelevant", 0) > 0:
      suggestions.append(
        "Refine system prompt with explicit instructions to stay on-topic and address the user question directly"
      )
    if categories.get("incomplete", 0) > 0:
      suggestions.append(
        "Increase chunk size in RAG pipeline to reduce context fragmentation and improve retrieval coverage"
      )
    if categories.get("off_topic", 0) > 0:
      suggestions.append(
        "Add intent classification layer to route ambiguous queries before generation"
      )

    if len(suggestions) < 3:
      suggestions.extend([
        "Add few-shot examples showing complete answers to improve completeness",
        "Tune retrieval top-k and reranking to surface more relevant context",
        "Run periodic human calibration on judge scores to reduce evaluation drift",
      ])

    return suggestions[: max(3, len(suggestions))]


# ---------------------------------------------------------------------------
# Bonus — N-gram Evaluator (Framework comparison alternative)
# ---------------------------------------------------------------------------

def _bigrams(text: str) -> set[tuple[str, str]]:
  words = re.findall(r"\b\w+\b", text.lower())
  if len(words) < 2:
    return set()
  return {(words[i], words[i + 1]) for i in range(len(words) - 1)}


class NgramEvaluator:
  """Alternative evaluator using bigram overlap (bonus framework comparison)."""

  def evaluate_faithfulness(self, answer: str, context: str) -> float:
    answer_bg = _bigrams(answer)
    if not answer_bg:
      return 1.0
    context_bg = _bigrams(context or "")
    if not context_bg:
      return 0.0
    return _clamp(len(answer_bg & context_bg) / len(answer_bg))

  def evaluate_relevance(self, answer: str, question: str) -> float:
    question_bg = _bigrams(question)
    if not question_bg:
      return 1.0
    answer_bg = _bigrams(answer)
    return _clamp(len(answer_bg & question_bg) / len(question_bg))

  def evaluate_completeness(self, answer: str, expected: str) -> float:
    expected_bg = _bigrams(expected)
    if not expected_bg:
      return 1.0
    answer_bg = _bigrams(answer)
    return _clamp(len(answer_bg & expected_bg) / len(expected_bg))

  def run_full_eval(
    self,
    answer: str,
    question: str,
    context: str,
    expected: str,
  ) -> dict[str, float]:
    return {
      "faithfulness": self.evaluate_faithfulness(answer, context or ""),
      "relevance": self.evaluate_relevance(answer, question),
      "completeness": self.evaluate_completeness(answer, expected),
    }


if __name__ == "__main__":
  qa_pairs = [
    QAPair(
      question="What is RAG?",
      expected_answer="RAG stands for Retrieval-Augmented Generation, which combines retrieval with text generation.",
      context="RAG is a technique that retrieves relevant documents and uses them to ground LLM generation.",
      metadata={"difficulty": "easy", "category": "definition"},
    ),
  ]
  evaluator = RAGASEvaluator()
  runner = BenchmarkRunner()
  results = runner.run(qa_pairs, lambda q: "RAG retrieves documents to ground generation.", evaluator)
  print(runner.generate_report(results))
