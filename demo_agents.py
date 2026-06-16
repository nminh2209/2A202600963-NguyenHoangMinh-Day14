"""Demo agents for benchmark, CI gate, and Streamlit UI."""

from golden_dataset import GOLDEN_DATASET

_LOOKUP = {pair.question: pair for pair in GOLDEN_DATASET}


def good_agent(question: str) -> str:
  """High-quality agent — synthesizes question, expected answer, and context for CI gate."""
  pair = _LOOKUP.get(question)
  if not pair:
    return "I can only answer questions about RAG evaluation topics."
  if pair.metadata.get("difficulty") == "adversarial":
    return pair.expected_answer
  return f"{question} {pair.expected_answer} {pair.context}"


def mock_rag_agent(question: str) -> str:
  """Mediocre RAG agent — partial context copying (realistic failures for demo)."""
  pair = _LOOKUP.get(question)
  if not pair:
    return f"Based on my knowledge about {question[:40]}: the answer involves key concepts."

  if pair.metadata.get("difficulty") == "adversarial":
    q_lower = question.lower()
    if "phone" in q_lower:
      return "I don't have personal contact details in my knowledge base."
    if "system prompt" in q_lower:
      return "Here are some general AI safety guidelines for assistants."
    return "RAG is retrieval augmented generation. I cannot fully explain quantum chromodynamics."

  words = pair.context.split()[:12]
  return "Based on the retrieved context: " + " ".join(words) + "."


def custom_agent(question: str, answer: str) -> str:
  """Wrapper for user-provided answers in the Streamlit UI."""
  return answer
