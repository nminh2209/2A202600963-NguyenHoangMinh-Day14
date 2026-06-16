"""
Day 14 — AI Evaluation & Benchmarking Pipeline
AICB-P1: AI Practical Competency Program, Phase 1

Key concepts from lecture:
    - Evaluation = Scientific Method for AI (Hypothesis → Experiment → Measure → Conclude → Iterate)
    - 4 nhóm metrics: Task Completion, Answer Quality, RAG-Specific, Business
    - RAG pipeline metrics: Context Recall → Context Precision → Faithfulness → Answer Relevancy
    - LLM-as-Judge: rubric scoring 1-5, detect bias (positional, verbosity, self-preference)
    - Golden dataset: stratified sampling (5 Easy + 7 Medium + 5 Hard + 3 Adversarial)
    - Failure taxonomy: hallucination, irrelevant, incomplete, off_topic, refusal
    - 5 Whys method for root cause analysis
    - CI/CD integration: eval as quality gate (score < threshold = block deploy)
    - Continuous Improvement Loop: Evaluate → Analyze → Improve → Augment → Repeat

Instructions:
    1. Fill in every section marked with TODO.
    2. Do NOT change class/function signatures.
    3. Copy this file to solution/solution.py when done.
    4. Run: pytest tests/ -v
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Task 1 — Data Models (Golden Dataset + Evaluation Results)
# ---------------------------------------------------------------------------

@dataclass
class QAPair:
    """
    A question-answer pair for evaluation (part of the Golden Dataset).

    From lecture: Golden dataset cần có:
        - question: câu hỏi user
        - ground_truth (expected_answer): expert-written expected answer
        - context: source documents cần retrieve
        - metadata: difficulty (easy/medium/hard), category, source_docs

    Fields:
        question:        The question to answer.
        expected_answer: The reference/ground-truth answer (expert-written).
        context:         Source context (may be empty string if not applicable).
        metadata:        Optional metadata dict (difficulty, category, etc.).
    """
    # TODO: define fields
    # Hints:
    #   context: str = ""
    #   metadata: dict = field(default_factory=dict)
    pass


@dataclass
class EvalResult:
    """
    Evaluation result for a single Q&A pair.

    From lecture - RAG metrics pipeline:
        Question → Retriever → Context → Generator → Answer
        Each step has a metric: Context Recall, Context Precision, Faithfulness, Answer Relevancy

    From lecture - Score interpretation:
        0.8-1.0: Good (Monitor, maintain)
        0.6-0.8: Needs work (Analyze failures, iterate)
        < 0.6: Significant issues (Deep investigation required)

    Fields:
        qa_pair:        The original QAPair.
        actual_answer:  What the agent actually returned.
        faithfulness:   Float 0-1, how grounded the answer is in context.
        relevance:      Float 0-1, how relevant the answer is to the question.
        completeness:   Float 0-1, how complete the answer is vs expected.
        passed:         True if all three scores >= 0.5.
        failure_type:   None if passed, otherwise one of:
                        "hallucination", "irrelevant", "incomplete", "off_topic".
    """
    # TODO: define fields
    # Hints:
    #   failure_type: str | None = None
    pass

    def overall_score(self) -> float:
        """Compute the average of faithfulness, relevance, and completeness.

        Returns:
            (faithfulness + relevance + completeness) / 3.0

        TODO: Return mean of the three metric scores
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Task 2 — RAGAS Evaluator (Simplified word-overlap heuristic)
# ---------------------------------------------------------------------------
# In production, replace with actual RAGAS framework:
#   from ragas import evaluate
#   from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision
#
# Or DeepEval:
#   from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
#   assert_test(test_case, [faithfulness, hallucination])
#
# Or TruLens:
#   from trulens.core import Feedback
#   f_groundedness = Feedback(provider.groundedness_measure_with_cot_reasons)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Lowercase word tokenization, ignoring punctuation."""
    return set(re.findall(r"\b\w+\b", text.lower()))


class RAGASEvaluator:
    """
    Evaluates RAG pipeline outputs using RAGAS-inspired heuristics.

    All metrics use word overlap rather than LLM calls for simplicity.
    Replace with actual LLM-based evaluation in production.
    """

    def evaluate_faithfulness(self, answer: str, context: str) -> float:
        """
        Measure how grounded the answer is in the context.

        Heuristic:
            answer_tokens = _tokenize(answer)
            context_tokens = _tokenize(context)
            faithfulness = |answer_tokens ∩ context_tokens| / |answer_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if answer is empty.

        Returns:
            float in [0.0, 1.0] — 1.0 = fully grounded in context.
        """
        # TODO
        raise NotImplementedError("Implement evaluate_faithfulness")

    def evaluate_relevance(self, answer: str, question: str) -> float:
        """
        Measure how relevant the answer is to the question.

        Heuristic:
            relevance = |answer_tokens ∩ question_tokens| / |question_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if question is empty.

        Returns:
            float in [0.0, 1.0]
        """
        # TODO
        raise NotImplementedError("Implement evaluate_relevance")

    def evaluate_completeness(self, answer: str, expected: str) -> float:
        """
        Measure how well the answer covers the expected answer.

        Heuristic:
            completeness = |answer_tokens ∩ expected_tokens| / |expected_tokens|
            Clamp to [0.0, 1.0]. Return 1.0 if expected is empty.

        Returns:
            float in [0.0, 1.0]
        """
        # TODO
        raise NotImplementedError("Implement evaluate_completeness")

    def run_full_eval(
        self,
        answer: str,
        question: str,
        context: str,
        expected: str,
    ) -> EvalResult:
        """
        Run all three evaluations and combine into an EvalResult.

        passed = True if all three scores >= 0.5.

        failure_type determination (first match wins):
            faithfulness < 0.3  → "hallucination"
            relevance < 0.3     → "irrelevant"
            completeness < 0.3  → "incomplete"
            otherwise if failed → "off_topic"

        Returns:
            EvalResult with all fields populated.
        """
        # TODO
        raise NotImplementedError("Implement run_full_eval")


# ---------------------------------------------------------------------------
# Task 3 — LLM Judge
# ---------------------------------------------------------------------------
# From lecture:
#   - Judge LLM nhận: question + agent answer + reference answer + rubric
#   - Judge trả về: Score 1-5 + Rationale
#   - Best practices: multiple judges, randomize order, calibrate against human
#   - Biases: positional, verbosity, self-preference
#   - Rubric template:
#       5 = Correct, complete, well-cited
#       4 = Mostly correct, minor gaps
#       3 = Partially correct, some errors
#       2 = Significant errors or missing info
#       1 = Wrong or irrelevant
# ---------------------------------------------------------------------------

class LLMJudge:
    """
    Uses an LLM to score AI responses according to a rubric.
    """

    def __init__(self, judge_llm_fn: Callable[[str], str]) -> None:
        # TODO: store judge_llm_fn
        pass

    def score_response(
        self,
        question: str,
        answer: str,
        rubric: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Score an AI response using the judge LLM.

        Args:
            question: The original question.
            answer:   The AI's answer to score.
            rubric:   Dict mapping criterion name → description.
                      Example: {"accuracy": "Is the answer factually correct?",
                                "clarity": "Is the answer clear and well-structured?"}

        Behavior:
            1. Build a judge prompt that includes the question, answer, and rubric.
            2. Call judge_llm_fn(prompt).
            3. Parse the response for scores.

        For simplicity, if the LLM response can't be parsed as JSON scores,
        return a default score of 0.5 for each criterion.

        Returns:
            {
                "scores":    dict[str, float],  # criterion → score 0-1
                "reasoning": str,               # raw LLM explanation
            }
        """
        # TODO
        raise NotImplementedError("Implement score_response")

    def detect_bias(self, scores_batch: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Detect potential bias patterns in a batch of judge scores.

        Checks:
            positional_bias: Check if first response consistently scores higher
            leniency_bias:   Average score > 0.8 across all criteria
            severity_bias:   Average score < 0.3 across all criteria

        Args:
            scores_batch: List of score dicts from score_response().

        Returns:
            {
                "positional_bias": bool,
                "leniency_bias":   bool,
                "severity_bias":   bool,
            }
        """
        # TODO
        raise NotImplementedError("Implement detect_bias")


# ---------------------------------------------------------------------------
# Task 4 — Benchmark Runner
# ---------------------------------------------------------------------------
# From lecture:
#   - CI/CD integration: Framework + CI/CD = quality gate tự động
#   - Agent với faithfulness < 0.7 → không được deploy
#   - Regression = metric drop > 0.05 vs baseline
#   - Triggers: mỗi code release, mỗi prompt change, trước demo/launch
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """
    Runs a full evaluation benchmark.
    """

    def run(
        self,
        qa_pairs: list[QAPair],
        agent_fn: Callable[[str], str],
        evaluator: RAGASEvaluator,
    ) -> list[EvalResult]:
        """
        Run all QA pairs through the agent and evaluate each result.

        Args:
            qa_pairs:   List of QAPair objects.
            agent_fn:   Function str → str (the agent's answer function).
            evaluator:  RAGASEvaluator instance.

        Returns:
            List of EvalResult, one per qa_pair.
        """
        # TODO: for each pair, call agent_fn(pair.question), then evaluator.run_full_eval
        raise NotImplementedError("Implement BenchmarkRunner.run")

    def generate_report(self, results: list[EvalResult]) -> dict[str, Any]:
        """
        Generate an aggregate report from evaluation results.

        Returns:
            {
                "total":            int,
                "passed":           int,
                "pass_rate":        float,  # passed / total
                "avg_faithfulness": float,
                "avg_relevance":    float,
                "avg_completeness": float,
                "failure_types":    dict[str, int],  # type → count
            }
        """
        # TODO
        raise NotImplementedError("Implement generate_report")

    def run_regression(self, new_results: list, baseline_results: list) -> dict:
        """Compare new evaluation results against a baseline.

        A regression is when a metric's average drops by more than 0.05 vs baseline.

        Args:
            new_results: List of EvalResult instances (current run)
            baseline_results: List of EvalResult instances (reference/baseline)

        Returns:
            dict with keys:
              - 'new_avg_faithfulness': float
              - 'new_avg_relevance': float
              - 'new_avg_completeness': float
              - 'baseline_avg_faithfulness': float
              - 'baseline_avg_relevance': float
              - 'baseline_avg_completeness': float
              - 'regressions': list[str] — names of metrics that regressed
              - 'passed': bool — True if no regressions

        TODO: Compute avg per metric, compare, list regressions, set passed flag
        """
        raise NotImplementedError

    def identify_failures(
        self,
        results: list[EvalResult],
        threshold: float = 0.5,
    ) -> list[EvalResult]:
        """
        Return EvalResults where any score is below threshold.

        Args:
            results:   Full list of EvalResults.
            threshold: Minimum acceptable score for any metric.

        Returns:
            List of failing EvalResults.
        """
        # TODO
        raise NotImplementedError("Implement identify_failures")


# ---------------------------------------------------------------------------
# Task 5 — Failure Analyzer
# ---------------------------------------------------------------------------
# From lecture:
#   Failure Taxonomy:
#     - hallucination: bịa thông tin → faithfulness guardrail yếu
#     - irrelevant: không giải quyết câu hỏi → prompt ambiguous
#     - incomplete: bỏ sót thông tin → context window nhỏ, retrieval thiếu
#     - off_topic: trả lời chủ đề khác → intent detection sai
#     - refusal: từ chối khi nên trả lời → guardrails quá chặt
#
#   5 Whys Method: hỏi "Tại sao?" liên tục cho đến root cause
#   Failure Clustering: fix 1 root cause giải quyết nhiều failures cùng lúc
#   Continuous Improvement: Evaluate → Analyze → Improve → Augment → Repeat
# ---------------------------------------------------------------------------

class FailureAnalyzer:
    """
    Analyzes failed evaluation results to identify patterns and suggest fixes.
    """

    def categorize_failures(
        self, failures: list[EvalResult]
    ) -> dict[str, int]:
        """
        Count failures by failure_type.

        Returns:
            dict mapping failure_type → count.
            Example: {"hallucination": 3, "irrelevant": 2, "incomplete": 5}
        """
        # TODO
        raise NotImplementedError("Implement categorize_failures")

    def find_root_cause(self, failure: EvalResult) -> str:
        """
        Suggest a root cause for a single failure based on its scores.

        Returns one of these strings based on which score is lowest:
            "Context is missing or irrelevant — improve retrieval"
            "Answer does not address the question — improve prompt clarity"
            "Answer is missing key information — increase context window or improve generation"
            "Multiple issues detected — review full pipeline"
        """
        # TODO: compare faithfulness, relevance, completeness, return appropriate string
        raise NotImplementedError("Implement find_root_cause")

    def generate_improvement_log(self, failures: list, suggestions: list[str]) -> str:
        """Generate a Markdown table logging failures and improvement actions.

        Format:
        | Failure ID | Type | Root Cause | Suggested Fix | Status |
        |------------|------|------------|---------------|--------|
        | F001       | ...  | ...        | ...           | Open   |

        Args:
            failures: List of EvalResult instances where passed=False
            suggestions: List of suggestion strings (one per failure, can be shorter list)

        Returns:
            Markdown table string with a row per failure. Status is always "Open".

        TODO: Build markdown table with failure details + matched suggestions
        """
        raise NotImplementedError

    def generate_improvement_suggestions(
        self, failures: list[EvalResult]
    ) -> list[str]:
        """
        Generate a prioritized list of improvement suggestions based on failure patterns.

        Each suggestion should be a concrete, actionable string.

        Examples:
            "Increase chunk size in RAG pipeline to reduce context fragmentation"
            "Add few-shot examples showing complete answers to improve completeness"
            "Implement hallucination checker to filter unsupported claims"

        Returns:
            List of at least 3 suggestion strings (or fewer if failures is empty).
        """
        # TODO: analyze categorized failures and return suggestions
        raise NotImplementedError("Implement generate_improvement_suggestions")


# ---------------------------------------------------------------------------
# Entry point for manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Sample golden dataset (mini version — use 20 pairs in actual lab)
    # From lecture: stratified sampling = 5 Easy + 7 Medium + 5 Hard + 3 Adversarial
    qa_pairs = [
        # Easy — factual lookup
        QAPair(
            question="What is RAG?",
            expected_answer="RAG stands for Retrieval-Augmented Generation, which combines retrieval with text generation.",
            context="RAG is a technique that retrieves relevant documents and uses them to ground LLM generation.",
            metadata={"difficulty": "easy", "category": "definition"},
        ),
        QAPair(
            question="What is the capital of France?",
            expected_answer="Paris is the capital of France.",
            context="France is a country in Western Europe. Its capital city is Paris.",
            metadata={"difficulty": "easy", "category": "factual"},
        ),
        # Medium — multi-step reasoning
        QAPair(
            question="Explain backpropagation and why it matters for training",
            expected_answer="Backpropagation is an algorithm for training neural networks by computing gradients efficiently, enabling deep learning models to learn from errors.",
            context="Neural networks learn through gradient descent. Backpropagation efficiently computes these gradients layer by layer.",
            metadata={"difficulty": "medium", "category": "explanation"},
        ),
        # Hard — ambiguous
        QAPair(
            question="Should I use RAG or fine-tuning for my chatbot?",
            expected_answer="It depends on the use case: RAG is better for frequently updated knowledge, fine-tuning for consistent style/behavior. Consider cost, latency, and data freshness.",
            context="RAG retrieves external documents at inference time. Fine-tuning modifies model weights during training.",
            metadata={"difficulty": "hard", "category": "comparison"},
        ),
        # Adversarial — out-of-scope
        QAPair(
            question="What is the meaning of life?",
            expected_answer="This question is outside the scope of this system. I can help with AI and technology questions.",
            context="This is an AI assistant specialized in technology topics.",
            metadata={"difficulty": "adversarial", "category": "out_of_scope"},
        ),
    ]

    evaluator = RAGASEvaluator()
    runner = BenchmarkRunner()

    def mock_agent(question: str) -> str:
        """Simple mock agent for testing. Replace with your actual agent."""
        return f"Based on my knowledge: {question[:30]}... The answer involves key concepts."

    # Run benchmark
    results = runner.run(qa_pairs, mock_agent, evaluator)
    report = runner.generate_report(results)
    print("=== Benchmark Report ===")
    for k, v in report.items():
        print(f"  {k}: {v}")

    # Identify and analyze failures
    failures = runner.identify_failures(results, threshold=0.5)
    print(f"\n=== Failures ({len(failures)}) ===")
    analyzer = FailureAnalyzer()

    # Categorize (from lecture: cluster before fix)
    categories = analyzer.categorize_failures(failures)
    print("Failure Categories:", categories)

    # Root cause for each failure (from lecture: 5 Whys)
    for f in failures:
        cause = analyzer.find_root_cause(f)
        print(f"  Root cause: {cause}")

    # Improvement suggestions (from lecture: continuous improvement loop)
    suggestions = analyzer.generate_improvement_suggestions(failures)
    print("\nImprovement Suggestions:")
    for s in suggestions:
        print(f"  - {s}")

    # Generate improvement log (Markdown table)
    log = analyzer.generate_improvement_log(failures, suggestions)
    print("\n=== Improvement Log ===")
    print(log)
