"""
Day 14 — RAG Evaluation Pipeline Demo
Streamlit UI to explore metrics, benchmarking, failure analysis, and framework comparison.

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from demo_agents import good_agent, mock_rag_agent
from golden_dataset import GOLDEN_DATASET
from scripts.framework_compare import compare_frameworks
from solution.solution import (
  BenchmarkRunner,
  FailureAnalyzer,
  LLMJudge,
  NgramEvaluator,
  RAGASEvaluator,
)

st.set_page_config(
  page_title="RAG Evaluation Pipeline",
  page_icon="📊",
  layout="wide",
)

AGENTS = {
  "Good agent (passes CI gate)": good_agent,
  "Mock RAG agent (realistic failures)": mock_rag_agent,
}


def _score_color(value: float) -> str:
  if value >= 0.8:
    return "🟢"
  if value >= 0.6:
    return "🟡"
  return "🔴"


def tab_single_eval() -> None:
  st.header("Single Q&A Evaluation")
  st.caption("Score one answer with RAGAS-inspired metrics + custom context utilization.")

  col1, col2 = st.columns(2)
  with col1:
    question = st.text_area("Question", "What does RAG stand for?", height=80)
    context = st.text_area(
      "Retrieved Context",
      "RAG is Retrieval-Augmented Generation, combining retrieval with LLM generation.",
      height=100,
    )
  with col2:
    expected = st.text_area(
      "Expected Answer",
      "RAG stands for Retrieval-Augmented Generation.",
      height=80,
    )
    answer = st.text_area(
      "Agent Answer",
      "RAG stands for Retrieval-Augmented Generation, which combines retrieval with generation.",
      height=100,
    )

  if st.button("Evaluate", type="primary"):
    ev = RAGASEvaluator()
    result = ev.run_full_eval(answer, question, context, expected)
    util = ev.evaluate_context_utilization(answer, context)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Faithfulness", f"{result.faithfulness:.2f}", help="Answer grounded in context?")
    m2.metric("Relevance", f"{result.relevance:.2f}", help="Addresses the question?")
    m3.metric("Completeness", f"{result.completeness:.2f}", help="Covers expected answer?")
    m4.metric("Overall", f"{result.overall_score():.2f}")
    m5.metric("Context Utilization", f"{util:.2f}", help="Custom metric: context used in answer")

    status = "PASSED" if result.passed else f"FAILED ({result.failure_type})"
    st.info(f"**Status:** {status}")

    chart_data = {
      "Metric": ["Faithfulness", "Relevance", "Completeness", "Context Util."],
      "Score": [result.faithfulness, result.relevance, result.completeness, util],
    }
    st.bar_chart(chart_data, x="Metric", y="Score")


def tab_benchmark() -> None:
  st.header("Golden Dataset Benchmark")
  st.caption("Run all 20 stratified QA pairs (5E + 7M + 5H + 3A) through an agent.")

  agent_name = st.selectbox("Agent", list(AGENTS.keys()))
  threshold = st.slider("Failure threshold", 0.0, 1.0, 0.5, 0.05)

  if st.button("Run Benchmark", type="primary"):
    runner = BenchmarkRunner()
    evaluator = RAGASEvaluator()
    results = runner.run(GOLDEN_DATASET, AGENTS[agent_name], evaluator)
    report = runner.generate_report(results)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pass Rate", f"{report['pass_rate']:.0%}")
    c2.metric("Avg Faithfulness", f"{report['avg_faithfulness']:.2f}")
    c3.metric("Avg Relevance", f"{report['avg_relevance']:.2f}")
    c4.metric("Avg Completeness", f"{report['avg_completeness']:.2f}")

    rows = []
    for pair, r in zip(GOLDEN_DATASET, results):
      rows.append({
        "ID": pair.metadata["id"],
        "Difficulty": pair.metadata["difficulty"],
        "Question": pair.question[:45] + ("..." if len(pair.question) > 45 else ""),
        "Faithfulness": round(r.faithfulness, 2),
        "Relevance": round(r.relevance, 2),
        "Completeness": round(r.completeness, 2),
        "Overall": round(r.overall_score(), 2),
        "Passed": r.passed,
        "Failure": r.failure_type or "-",
      })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if report["failure_types"]:
      st.subheader("Failure Distribution")
      st.bar_chart(report["failure_types"])

    st.session_state["benchmark_results"] = results
    st.session_state["benchmark_report"] = report
    st.session_state["benchmark_threshold"] = threshold


def tab_failure_analysis() -> None:
  st.header("Failure Analysis")
  st.caption("Categorize failures, find root causes, and generate improvement actions.")

  if "benchmark_results" not in st.session_state:
    st.warning("Run a benchmark first (Benchmark tab), or run one now.")
    if st.button("Quick run with Mock RAG agent"):
      runner = BenchmarkRunner()
      st.session_state["benchmark_results"] = runner.run(
        GOLDEN_DATASET, mock_rag_agent, RAGASEvaluator()
      )
      st.session_state["benchmark_threshold"] = 0.5
      st.rerun()
    return

  runner = BenchmarkRunner()
  analyzer = FailureAnalyzer()
  results = st.session_state["benchmark_results"]
  threshold = st.session_state.get("benchmark_threshold", 0.5)
  failures = runner.identify_failures(results, threshold=threshold)

  st.metric("Failures", f"{len(failures)} / {len(results)}")

  if not failures:
    st.success("No failures at current threshold.")
    return

  categories = analyzer.categorize_failures(failures)
  st.subheader("Failure Categories")
  st.bar_chart(categories)

  suggestions = analyzer.generate_improvement_suggestions(failures)
  st.subheader("Improvement Suggestions")
  for s in suggestions:
    st.markdown(f"- {s}")

  log = analyzer.generate_improvement_log(failures, suggestions)
  st.subheader("Improvement Log")
  st.markdown(log)

  with st.expander("Per-failure root causes"):
    for i, f in enumerate(failures[:10], 1):
      qid = f.qa_pair.metadata.get("id", f"F{i}")
      cause = analyzer.find_root_cause(f)
      st.markdown(f"**{qid}** ({f.failure_type}): {cause}")


def tab_regression() -> None:
  st.header("Regression Testing")
  st.caption("Compare a new run against baseline — flag metric drops > 0.05.")

  col1, col2 = st.columns(2)
  with col1:
    st.subheader("Baseline")
    baseline_agent = st.selectbox("Baseline agent", list(AGENTS.keys()), key="base_agent")
  with col2:
    st.subheader("New (candidate)")
    new_agent = st.selectbox(
      "New agent",
      list(AGENTS.keys()),
      index=1,
      key="new_agent",
    )

  if st.button("Compare Runs", type="primary"):
    runner = BenchmarkRunner()
    evaluator = RAGASEvaluator()
    baseline = runner.run(GOLDEN_DATASET, AGENTS[baseline_agent], evaluator)
    new = runner.run(GOLDEN_DATASET, AGENTS[new_agent], evaluator)
    reg = runner.run_regression(new, baseline)

    passed = reg["passed"]
    st.success("No regressions — safe to deploy") if passed else st.error(
      f"Regressions detected: {', '.join(reg['regressions'])}"
    )

    metrics = ["faithfulness", "relevance", "completeness"]
    rows = []
    for m in metrics:
      rows.append({
        "Metric": m.capitalize(),
        "Baseline": round(reg[f"baseline_avg_{m}"], 3),
        "New": round(reg[f"new_avg_{m}"], 3),
        "Delta": round(reg[f"new_avg_{m}"] - reg[f"baseline_avg_{m}"], 3),
        "Regressed": m in reg["regressions"],
      })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def tab_framework_compare() -> None:
  st.header("Framework Comparison (Bonus)")
  st.caption("RAGAS word-overlap vs N-gram bigram overlap on the same dataset.")

  agent_name = st.selectbox("Agent for comparison", list(AGENTS.keys()), key="fw_agent")
  if st.button("Run Comparison", type="primary"):
    data = compare_frameworks(AGENTS[agent_name])
    avg = data["averages"]

    c1, c2 = st.columns(2)
    with c1:
      st.subheader("RAGAS Heuristic")
      st.json(avg["ragas"])
    with c2:
      st.subheader("N-gram Evaluator")
      st.json(avg["ngram"])

    st.info(data["insight"])

    diff_rows = []
    for row in data["per_pair"]:
      diff_rows.append({
        "ID": row["id"],
        "RAGAS Overall": row["ragas_overall"],
        "N-gram Overall": row["ngram_overall"],
        "Delta": round(row["ngram_overall"] - row["ragas_overall"], 3),
      })
    st.dataframe(diff_rows, use_container_width=True, hide_index=True)


def tab_llm_judge() -> None:
  st.header("LLM-as-Judge Demo")
  st.caption("Score responses with a rubric. Uses a mock judge unless you paste custom JSON output.")

  question = st.text_input("Question", "What is faithfulness in RAG evaluation?")
  answer = st.text_input(
    "Answer",
    "Faithfulness measures whether the generated answer is supported by retrieved context.",
  )

  st.subheader("Rubric")
  rubric = {
    "correctness": "Is the answer factually correct?",
    "completeness": "Does it fully explain the concept?",
    "relevance": "Does it address the question directly?",
  }

  mock_response = st.text_area(
    "Mock judge JSON response",
    '{"correctness": 0.9, "completeness": 0.75, "relevance": 0.85}',
    help="Simulates what an LLM judge would return",
  )

  if st.button("Score with Judge", type="primary"):
    judge = LLMJudge(judge_llm_fn=lambda _: mock_response)
    result = judge.score_response(question, answer, rubric)

    st.subheader("Scores")
    for criterion, score in result["scores"].items():
      st.progress(score, text=f"{criterion}: {score:.2f}")

    st.subheader("Bias Detection Demo")
    batch = [
      result,
      judge.score_response(question, "Wrong answer about retrieval speed.", rubric),
    ]
    bias = judge.detect_bias(batch)
    b1, b2, b3 = st.columns(3)
    b1.metric("Positional Bias", "Yes" if bias["positional_bias"] else "No")
    b2.metric("Leniency Bias", "Yes" if bias["leniency_bias"] else "No")
    b3.metric("Severity Bias", "Yes" if bias["severity_bias"] else "No")

    with st.expander("Raw judge reasoning"):
      st.code(result["reasoning"])


def main() -> None:
  st.title("📊 Day 14 — RAG Evaluation Pipeline")
  st.markdown(
    "Interactive demo of **RAGAS metrics**, **benchmarking**, **failure analysis**, "
    "**regression testing**, and **LLM-as-Judge**."
  )

  tabs = st.tabs([
    "Single Eval",
    "Benchmark",
    "Failure Analysis",
    "Regression",
    "Framework Compare",
    "LLM Judge",
  ])

  with tabs[0]:
    tab_single_eval()
  with tabs[1]:
    tab_benchmark()
  with tabs[2]:
    tab_failure_analysis()
  with tabs[3]:
    tab_regression()
  with tabs[4]:
    tab_framework_compare()
  with tabs[5]:
    tab_llm_judge()

  with st.sidebar:
    st.header("About")
    st.markdown(
      "**Golden dataset:** 20 QA pairs\n\n"
      "- 5 Easy\n- 7 Medium\n- 5 Hard\n- 3 Adversarial"
    )
    st.markdown("**Bonus features:**")
    st.markdown(
      "- Custom metric: context utilization\n"
      "- N-gram framework comparison\n"
      "- CI/CD quality gate (GitHub Actions)"
    )
    if st.button("Run pytest"):
      import subprocess
      proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
      )
      st.code(proc.stdout + proc.stderr)


if __name__ == "__main__":
  main()
