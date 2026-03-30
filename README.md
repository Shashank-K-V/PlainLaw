# Viveka ⚖️

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=flat&logo=chainlink&logoColor=white)
![Llama](https://img.shields.io/badge/Llama_3.1_8B-Meta-0064E0?style=flat&logo=meta&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![LM Studio](https://img.shields.io/badge/LM_Studio-local-black?style=flat&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-E92063?style=flat&logo=pydantic&logoColor=white)

> *Viveka* (विवेक) — Sanskrit for **discernment** · the ability to see clearly and judge wisely.

A 100% on-device AI legal document analyser. Upload any contract — Viveka extracts individual clauses, scores each one for risk, and returns plain-English explanations with lawyer questions to ask before signing. Built on Llama 3.1 8B via LM Studio for local inference, LangChain for orchestration, PyMuPDF for PDF parsing, Pydantic v2 for structured outputs, and Streamlit for the UI. Zero data leaves the machine — designed for sensitive legal documents where privacy is non-negotiable.

---

## Features

- **Fully offline inference** — runs entirely on-device via LM Studio, no external API calls
- **PDF + TXT ingestion** — PyMuPDF extracts and segments raw contract text into discrete clauses
- **Structured output** — Pydantic v2 enforces typed JSON from the LLM, with three-stage fallback parsing
- **Risk scoring** — each clause classified as High Risk, Review Carefully, or Standard
- **Plain-English explanations** — concise summaries and "why it matters" rationale per clause
- **Lawyer questions** — auto-generated questions to raise with legal counsel before signing
- **Document summary** — contract type detection, top risks, and pre-sign checklist
- **PDF report export** — full colour-coded analysis exported via ReportLab
- **Privacy-first by design** — no telemetry, no cloud, no data retention

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM Orchestration | LangChain 0.3 |
| Local Inference | LM Studio + Llama 3.1 8B (MLX, 4-bit) |
| PDF Parsing | PyMuPDF (fitz) |
| Structured Output | Pydantic v2 + custom JSON extractor |
| UI | Streamlit |
| Report Export | ReportLab |

---

## Architecture

```
PDF / TXT
    │
    ▼
PyMuPDF Parser
(text extraction + clause segmentation + title extraction)
    │
    ▼
LangChain Chain
(prompt construction + chain execution per clause)
    │
    ▼
Llama 3.1 8B — LM Studio
(local inference, MLX-accelerated on Apple Silicon)
    │
    ▼
JSON Extractor
(direct parse → strip markdown fences → regex fallback)
    │
    ▼
Pydantic v2 Parser
(typed validation: ClauseAnalysis, DocumentSummary)
    │
    ▼
Streamlit UI
(colour-coded clause cards + summary tab + PDF export)
```

### Key Engineering Decisions

**Prompt-based structured output** — rather than relying on function-calling or tool-use (unsupported by many local models), the system prompt embeds a concrete JSON schema example. A three-stage extractor then recovers valid JSON even when the model wraps output in markdown fences or adds preamble text. Pydantic validates the final object.

**Clause-level processing** — contracts are segmented before LLM calls, giving per-clause UI granularity while keeping each request within the 8K context window of 8B models.

**Risk calibration via prompt engineering** — explicit few-shot examples of high/medium/low clauses in the system prompt prevent the model from defaulting to extreme labels — the key fix that resolved over-aggressive risk scoring in early iterations.

---

## Run Locally

**1. Install LM Studio and load the model**

Download [LM Studio](https://lmstudio.ai), go to the **Discover** tab, search for `llama-3.1-8b-instruct`, filter by **MLX**, and download `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`. Open the **Local Server** tab, set context length to `8192`, and click **Start Server** — runs at `http://localhost:1234`.

**2. Clone the repo**

```bash
git clone https://github.com/Shashank-K-V/viveka.git
cd viveka
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run**

```bash
streamlit run app.py
```

Open `http://localhost:8501`, set the LM Studio URL to `http://localhost:1234/v1`, upload a contract, and click **Analyse Contract**.

### Recommended Models

| Model | RAM | Speed (M-series) | Quality |
|---|---|---|---|
| `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` | ~5 GB | ~50 tok/s | ★★★★☆ |
| `mlx-community/Mistral-7B-Instruct-v0.3-4bit` | ~4.5 GB | ~50 tok/s | ★★★★☆ |
| `mlx-community/Llama-3.2-3B-Instruct-4bit` | ~2 GB | ~80 tok/s | ★★★☆☆ |

> On Apple Silicon (M1–M4) always use the **MLX** variant — 3–5× faster than GGUF on the same hardware.

---

## Project Structure

```
viveka/
├── app.py              # Streamlit UI — rendering, state management, export
├── analyzer.py         # LangChain chains, LLM calls, JSON extraction
├── parser.py           # PyMuPDF text extraction and clause segmentation
├── models.py           # Pydantic v2 schemas (ClauseAnalysis, DocumentSummary)
├── exporter.py         # ReportLab PDF report generation
├── sample_contract.txt            # Employment Agreement — 13 clauses
├── sample_complex_contract.txt    # Software Development Agreement — 19 clauses
└── requirements.txt
```

---

## Privacy

> **All inference runs entirely on your machine.**
> No contract text, no clause data, and no analysis results are transmitted to any external server or API.
> Viveka is designed for legal documents — confidentiality is a first-class requirement, not an afterthought.

---

## Limitations

- Not a substitute for qualified legal advice — treat flagged clauses as starting points for review
- Scanned PDFs with no embedded text require OCR pre-processing before upload
- Optimised for English-language contracts; other languages are unsupported
- Risk classification accuracy scales with model size — 8B models handle standard contract types well; complex instruments benefit from larger models

---

## Roadmap

- [ ] Deploy to Hugging Face Spaces
- [ ] Async parallel clause processing
- [ ] Clause diff mode — compare two contract versions
- [ ] Contract type–specific risk rubrics (lease / employment / SaaS)
- [ ] Inline highlight mode — full contract view with colour overlays

---

## Swap to Cloud API

One change in `analyzer.py` switches inference from local to any OpenAI-compatible cloud API:

```python
def build_llm(**kwargs):
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)
```

No other code changes needed — the interface is identical.

---

## License

MIT
