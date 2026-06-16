# Ngày 14 — AI Evaluation & Benchmarking Pipeline

**AICB-P1 · Phase 1 · Ngày 14 trong 15**

---

## Mục tiêu

Sau lab này, bạn sẽ:
1. Xây dựng **pipeline đánh giá tự động** để benchmark AI agent trên 20 test cases
2. Áp dụng các metrics lấy cảm hứng từ **RAGAS** (faithfulness, relevance, completeness)
3. Triển khai **LLM-as-Judge** với rubric scoring 1–5 và phát hiện bias
4. Thiết kế **golden dataset** với stratified sampling (easy/medium/hard/adversarial)
5. Thực hiện **failure analysis** có hệ thống bằng 5 Whys và failure clustering
6. Hiểu cách tích hợp evaluation vào **CI/CD** như quality gate

---

## Bối Cảnh Lý Thuyết

### Evaluation = Scientific Method Cho AI

```
Hypothesis → Experiment (chạy benchmark) → Measure (frameworks) → Conclude → Iterate
```

**Nguyên tắc:** Evaluation phải LẶP LẠI ĐƯỢC, SO SÁNH ĐƯỢC, và CHẠY TỰ ĐỘNG ĐƯỢC.

### 3 Loại Evaluation

| Loại | Khi nào | Tool |
|------|---------|------|
| **Offline** | Mỗi release, mỗi prompt change | RAGAS, DeepEval, TruLens |
| **Online** | Continuous, real traffic | TruLens, Langfuse |
| **Human** | Weekly, high-stakes | Annotation UI, spreadsheet |

> ⚠️ Chỉ offline = không biết production quality. Chỉ human = không scale. Cần **kết hợp cả 3**.

### 4 Nhóm Metrics

| Nhóm | Metrics |
|------|---------|
| **Task Completion** | Binary pass/fail, partial credit, steps completed |
| **Answer Quality** | Accuracy, completeness, coherence, citation accuracy |
| **RAG-Specific** | Faithfulness, answer relevancy, context recall, context precision |
| **Business** | User satisfaction, time saved, cost/interaction, adoption rate |

### RAG Metrics Pipeline

```
Question → Retriever → Context → Generator → Answer
              ↓            ↓          ↓           ↓
         Context       Context   Faithfulness  Answer
          Recall      Precision                Relevancy
```

**Cách đọc kết quả:**
- Context Recall thấp → retrieve thiếu evidence
- Context Precision thấp → retrieve thừa, noise nhiều
- Faithfulness thấp → hallucinate (bịa thông tin)
- Answer Relevancy thấp → trả lời lạc đề

### LLM-as-Judge

Sử dụng một LLM riêng (GPT-4, Claude) để chấm điểm response theo rubric:
- Judge nhận: question + agent answer + reference answer + rubric
- Judge trả về: score 1–5 + rationale (giải thích)
- **Biases cần xử lý:** Position bias, Verbosity bias, Self-preference bias
- **Best practice:** Multiple judges, randomize order, calibrate against human

### Golden Dataset Design

| Phân bổ 20 test cases | Mục đích |
|----------------------|----------|
| **5 Easy** | Factual lookup, single-doc |
| **7 Medium** | Multi-step reasoning, 2–3 docs |
| **5 Hard** | Complex/ambiguous, nhiều cách hiểu |
| **3 Adversarial** | Out-of-scope, cố tình phá |

### Failure Taxonomy

| Loại | Triệu chứng | Root cause thường gặp |
|------|-------------|----------------------|
| `hallucination` | Bịa thông tin không có trong context | Faithfulness guardrail yếu |
| `irrelevant` | Không giải quyết câu hỏi | Prompt ambiguous, routing sai |
| `incomplete` | Bỏ sót thông tin quan trọng | Context window quá nhỏ, retrieval thiếu |
| `off_topic` | Trả lời về chủ đề khác | Intent detection sai |
| `refusal` | Từ chối khi nên trả lời | Guardrails quá chặt |

### 5 Whys Method

Phân tích root cause bằng cách hỏi "Tại sao?" liên tục cho đến khi tìm ra nguyên nhân gốc.
Fix đúng root cause sẽ giải quyết hàng loạt failures tương tự.

### 3 Evaluation Frameworks

| Framework | Focus | Best for |
|-----------|-------|----------|
| **RAGAS** | RAG metrics chuẩn hóa | RAG pipeline CI/CD |
| **DeepEval** | LLM unit testing (pytest-native) | CI/CD assertions, safety metrics |
| **TruLens** | Feedback functions + production | Online + offline monitoring |

### CI/CD Integration

Framework + CI/CD = **quality gate** tự động:
- Agent với faithfulness < 0.7 → không được deploy (giống failed unit test)
- DeepEval: `deepeval test run test_eval.py` trong GitHub Actions
- RAGAS/TruLens: custom script + threshold check

---

## Nhiệm Vụ

### Nhiệm vụ 1: Data Models — `QAPair` và `EvalResult`
Định nghĩa các container dữ liệu cho evaluation pipeline.
- `QAPair`: question, expected_answer, context, metadata
- `EvalResult`: scores, passed flag, failure_type classification, overall_score()

### Nhiệm vụ 2: `RAGASEvaluator`
Triển khai 3 metrics RAGAS bằng word-overlap heuristic:
- `evaluate_faithfulness`: answer có grounded trong context không?
- `evaluate_relevance`: answer có trả lời đúng question không?
- `evaluate_completeness`: answer có cover hết expected answer không?
- `run_full_eval`: chạy cả 3 metrics, xác định failure_type

### Nhiệm vụ 3: `LLMJudge`
- `score_response`: dùng LLM để chấm response theo rubric (scoring 1–5)
- `detect_bias`: phát hiện positional bias, leniency bias, severity bias trong batch scores

### Nhiệm vụ 4: `BenchmarkRunner`
- `run`: chạy tất cả QA pairs qua agent + evaluator
- `generate_report`: tạo báo cáo tổng hợp (pass rate, avg scores, failure types)
- `run_regression`: so sánh new results vs baseline, phát hiện regression (drop > 0.05)
- `identify_failures`: lọc ra EvalResults có score dưới threshold

### Nhiệm vụ 5: `FailureAnalyzer`
- `categorize_failures`: nhóm failures theo type
- `find_root_cause`: đề xuất root cause dựa trên score pattern
- `generate_improvement_suggestions`: tạo danh sách fix ưu tiên
- `generate_improvement_log`: xuất Markdown table cho failure tracking

---

## Sản phẩm nộp bài

1. **`solution/solution.py`** — triển khai hoàn chỉnh tất cả TODO
2. **`exercises.md`** — golden dataset 20 QA pairs (5E + 7M + 5H + 3A) + benchmark results + rubric design
3. **`reflection.md`** — evaluation report: 3 worst failures với 5 Whys + improvement log + regression strategy

---

## Hướng dẫn thời gian lab

| Thời gian | Hoạt động |
|-----------|-----------|
| 0:00–0:20 | **Warm-up:** Hiểu RAGAS thresholds + position bias (exercises.md Phần 1) |
| 0:20–1:20 | **Core coding:** Triển khai tất cả TODO trong template.py |
| 1:20–2:20 | **Extended:** Tạo golden dataset 20 QA, chạy benchmark, thiết kế rubric (exercises.md Phần 3) |
| 2:20–2:50 | **Reflection:** Failure analysis 5 Whys + regression strategy (reflection.md) |
| 2:50–3:00 | **Wrap-up:** Chạy pytest, copy solution, nộp bài |

---

## Chạy kiểm thử

```bash
pytest tests/ -v
```

---

## Streamlit Demo UI

Interactive dashboard to explore the full evaluation pipeline:

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Tabs:**
- **Single Eval** — score one Q&A with all metrics + custom context utilization
- **Benchmark** — run 20-case golden dataset with good/mock agents
- **Failure Analysis** — categorize failures, root causes, improvement log
- **Regression** — compare baseline vs candidate agent (0.05 drop threshold)
- **Framework Compare** — RAGAS heuristic vs N-gram evaluator side-by-side
- **LLM Judge** — rubric scoring + bias detection demo

---

## Bonus Features (implemented)

| Bonus | Location | How to run |
|-------|----------|------------|
| Framework comparison (+10) | `scripts/framework_compare.py`, `NgramEvaluator` in `solution/solution.py` | `python scripts/framework_compare.py` |
| CI/CD integration (+5) | `.github/workflows/eval.yml`, `scripts/ci_eval_gate.py` | `python scripts/ci_eval_gate.py` |
| Custom metric (+5) | `evaluate_context_utilization()` on `RAGASEvaluator` | Visible in Streamlit Single Eval tab |

---

## Danh sách kiểm tra nộp bài

- [ ] `pytest tests/ -v` — tất cả kiểm thử đều pass
- [ ] `overall_score` trên `EvalResult` đã triển khai
- [ ] `run_regression` trên `BenchmarkRunner` đã triển khai
- [ ] `generate_improvement_log` trên `FailureAnalyzer` đã triển khai
- [ ] `exercises.md` — golden dataset 20 QA (stratified) + benchmark results + rubric design
- [ ] `reflection.md` — evaluation report với 3 failure analyses (5 Whys) + improvement log + CI/CD strategy
- [ ] `solution/solution.py` — bản sao template.py đã hoàn chỉnh

---

## Chấm điểm

| Tiêu chí | Điểm |
|----------|------|
| Tất cả kiểm thử pytest đều pass | 50 |
| Golden dataset 20 QA với stratified sampling đúng chuẩn | 15 |
| LLM-as-Judge rubric design có tiêu chí rõ ràng | 10 |
| Failure analysis (5 Whys) + improvement log | 15 |
| Chất lượng code, type hints, và regression strategy | 10 |
| **Tổng** | **100** |

---

## Bonus (thêm điểm)

- Chạy 2 frameworks khác nhau trên cùng dataset và so sánh scores (+10)
- Tích hợp evaluation vào CI/CD script (GitHub Actions hoặc tương tự) (+5)
- Thêm custom metric ngoài 3 metrics cơ bản (+5)
# Day_14_RAG_Evaluation
