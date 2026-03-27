# ⚖️ PlainLaw

**Plain English for legal documents — powered by a local LLM, fully private.**

PlainLaw is a Streamlit application that takes any contract (PDF or text), splits it into individual clauses, analyzes each one for risk using a locally running language model, and presents a colour-coded interactive report — with plain English explanations, risk reasoning, and lawyer questions for every clause.

No data leaves your machine. No API keys. No usage fees.

---

## Screenshots
<img width="1807" height="736" alt="PlainLaw" src="https://github.com/user-attachments/assets/728eb9ed-7dc4-4653-b9cd-0e5aaf7cd39c" />

> Contract view — colour-coded clause cards sorted high → medium → low risk

| Contract Tab | Summary Tab |
|---|---|
| Red left border = High Risk · Amber = Review · Green = Standard | Document summary, top risks, and downloadable PDF report |

---

## Features

- **Clause-level risk scoring** — each clause independently classified as High Risk / Review Carefully / Standard
- **Plain English explanations** — 2–3 sentence translation of legal language into plain English
- **Risk reasoning** — one-sentence explanation of *why* a clause is flagged
- **Auto-generated lawyer questions** — specific questions to ask before signing
- **Document summary** — contract type detection, top 3 risks, top 3 questions
- **PDF export** — full colour-coded report with ReportLab, ready to share
- **100% local** — runs on LM Studio with any OpenAI-compatible local model
- **Structured output** — Pydantic v2 validation on every LLM response; malformed JSON auto-recovered via regex extraction
- **PDF + TXT support** — PyMuPDF handles scanned and digital PDFs

---

## Architecture

```
plainlaw/
├── app.py          # Streamlit UI — upload, progress, contract + summary tabs
├── analyzer.py     # LangChain chains → LM Studio → JSON extraction → Pydantic
├── parser.py       # PyMuPDF text extraction + clause splitter + title extractor
├── models.py       # Pydantic schemas: ClauseAnalysis, DocumentSummary, AnalyzedClause
├── exporter.py     # ReportLab PDF report builder
└── requirements.txt
```

### How it works

```
PDF / TXT upload
      │
      ▼
 PyMuPDF extracts raw text
      │
      ▼
 Clause splitter
 (numbered sections → paragraph fallback → merge short fragments)
      │
      ▼
 For each clause ──────────────────────────────────────────────┐
      │                                                         │
      ▼                                                         │
 LangChain prompt → LM Studio (local LLM)                      │
      │                                                         │
      ▼                                                         │
 JSON extraction (direct → strip fences → regex fallback)      │
      │                                                         │
      ▼                                                         │
 Pydantic validation → AnalyzedClause ─────────────────────────┘
      │
      ▼
 Document summary chain (reads all clause analyses)
      │
      ▼
 Streamlit UI renders colour-coded cards + Summary tab + PDF export
```

### Key engineering decisions

**Structured output via prompt + JSON extraction** — instead of relying on function-calling or tool-use (which not all local models support), the system prompt provides a concrete JSON schema example, and a three-stage extractor recovers valid JSON even when the model wraps its output in markdown fences or adds preamble text. Pydantic validates the final object.

**Clause-level parallelism** — contracts are split into clauses before LLM processing, giving per-clause UI granularity for free and keeping each request well within the 8K context window of 8B models.

**Risk calibration via prompt engineering** — the system prompt includes explicit examples of high/medium/low clauses to prevent the model from defaulting to extreme labels. This was the key change that fixed over-aggressive risk scoring in early versions.

---

## Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM orchestration | LangChain + langchain-openai |
| Local inference | LM Studio (OpenAI-compatible API) |
| Structured output | Pydantic v2 + custom JSON extraction |
| PDF parsing | PyMuPDF (fitz) |
| PDF export | ReportLab |
| Language | Python 3.11+ |

---

## Setup

### Prerequisites

- Python 3.11+
- [LM Studio](https://lmstudio.ai) installed with a model downloaded

### Recommended models

| Model | RAM required | Speed on M-series | Quality |
|---|---|---|---|
| `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` | ~5 GB | ~50 tok/s | ★★★★☆ |
| `mlx-community/Mistral-7B-Instruct-v0.3-4bit` | ~4.5 GB | ~50 tok/s | ★★★★☆ |
| `mlx-community/Llama-3.2-3B-Instruct-4bit` | ~2 GB | ~80 tok/s | ★★★☆☆ |

> For Apple Silicon (M1/M2/M3/M4): always choose the **MLX** variant — it runs natively on the Neural Engine and is 3–5× faster than GGUF on the same hardware.

### Install

```bash
git clone https://github.com/yourusername/plainlaw.git
cd plainlaw
pip install -r requirements.txt
```

### Configure LM Studio

1. Open LM Studio → **Discover** tab
2. Search for `llama-3.1-8b-instruct`, filter by **MLX**
3. Download `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`
4. Go to **Local Server** tab (`⇄` icon)
5. Select the model, set **Context Length** to `8192`
6. Click **Start Server** — runs at `http://localhost:1234`

### Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Usage

1. Enter your LM Studio URL in the sidebar (default: `http://localhost:1234/v1`)
2. Upload a PDF or `.txt` contract
3. Adjust max clauses (default 30) — more clauses = slower but more thorough
4. Click **Analyze Contract**
5. Review clauses in the **Contract** tab, sorted high → medium → low risk
6. Check the **Summary** tab for the document overview and top risks
7. Click **Download PDF Report** to export a shareable report

---

## Sample contracts

Two sample contracts are included for testing:

| File | Type | Clauses | Notes |
|---|---|---|---|
| `sample_contract.txt` | Employment + NDA | 13 | Basic mix of risk levels |
| `sample_complex_contract.txt` | Software Development Services | 19 | Aggressive vendor terms, liability caps, indemnification traps |

---

## Limitations

- **Not legal advice** — PlainLaw is an educational tool. Always consult a qualified lawyer before signing any contract.
- **Risk scoring accuracy** — a local 8B model is good but not infallible. Treat flagged clauses as starting points for review, not definitive legal opinions.
- **Scanned PDFs** — PDFs that are images only (no embedded text) will extract empty. Use a scanned PDF with OCR pre-applied, or paste the text directly.
- **Very long contracts** — capped at 40 clauses by default to keep processing time reasonable. Increase the slider for longer documents.
- **Language** — optimised for English-language contracts only.

---

## Roadmap

- [ ] Deploy to Hugging Face Spaces (free permanent hosting)
- [ ] Clause comparison mode — diff two versions of the same contract
- [ ] Contract type–specific risk rubrics (lease vs employment vs SaaS)
- [ ] Async parallel clause processing for faster analysis
- [ ] Claude API backend option for higher-accuracy legal reasoning
- [ ] Highlight mode — render the full contract as a single document with inline colour highlights

---

## Upgrade path

Swap the local LLM for the Anthropic API in one change in `analyzer.py`:

```python
from langchain_anthropic import ChatAnthropic

def build_llm(**kwargs):
    return ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
```

```bash
pip install langchain-anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

Claude is significantly better at legal reasoning and consistency than a 7B local model. Haiku costs approximately $0.001 per contract.

---

## License

MIT — see `LICENSE`.

---

> Built with [LM Studio](https://lmstudio.ai), [LangChain](https://langchain.com), [Streamlit](https://streamlit.io), and [PyMuPDF](https://pymupdf.readthedocs.io).
