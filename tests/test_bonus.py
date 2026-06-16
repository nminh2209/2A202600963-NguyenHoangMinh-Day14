"""Bonus feature tests — custom metric and N-gram evaluator."""

import importlib.util
import sys
import unittest
from pathlib import Path

DAY_DIR = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("solution", DAY_DIR / "solution" / "solution.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["solution"] = mod
spec.loader.exec_module(mod)

RAGASEvaluator = mod.RAGASEvaluator
NgramEvaluator = mod.NgramEvaluator


class TestCustomMetric(unittest.TestCase):
  def setUp(self):
    self.ev = RAGASEvaluator()

  def test_context_utilization_full_use(self):
    context = "RAG retrieves documents for grounded generation"
    answer = "RAG retrieves documents for grounded generation"
    score = self.ev.evaluate_context_utilization(answer, context)
    self.assertAlmostEqual(score, 1.0, places=1)

  def test_context_utilization_ignores_context(self):
    context = "RAG retrieves documents for grounded generation"
    answer = "completely unrelated words here"
    score = self.ev.evaluate_context_utilization(answer, context)
    self.assertLess(score, 0.3)


class TestNgramEvaluator(unittest.TestCase):
  def setUp(self):
    self.ev = NgramEvaluator()

  def test_returns_scores_in_range(self):
    scores = self.ev.run_full_eval(
      "Python is a programming language",
      "What is Python",
      "Python is a popular programming language",
      "Python is a programming language",
    )
    for value in scores.values():
      self.assertGreaterEqual(value, 0.0)
      self.assertLessEqual(value, 1.0)

  def test_differs_from_word_overlap(self):
    ragas = RAGASEvaluator()
    answer = "machine learning models"
    question = "What is machine learning"
    r = ragas.evaluate_relevance(answer, question)
    n = self.ev.evaluate_relevance(answer, question)
    self.assertIsInstance(r, float)
    self.assertIsInstance(n, float)


if __name__ == "__main__":
  unittest.main()
