import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from models import ClauseAnalysis, DocumentSummary, AnalyzedClause


# ── Prompts ────────────────────────────────────────────────────────────────────

CLAUSE_SYSTEM = """You are a careful legal analyst. Analyze the contract clause and return ONLY a valid JSON object — no explanation, no markdown, no extra text.

Required format:
{{
  "risk_level": "high",
  "risk_reason": "one sentence explaining the risk",
  "plain_english": "2-3 sentence plain English explanation of what this clause means",
  "tags": ["tag1", "tag2"],
  "questions": ["question to ask a lawyer"]
}}

risk_level must be exactly one of: "high", "medium", "low"

Be precise — most clauses in a standard contract are "low". Only use "high" for genuinely dangerous terms.

Risk definitions:
- "high"   : use ONLY for clauses that are genuinely dangerous — unlimited IP assignment covering personal time, worldwide non-compete over 1 year, unlimited personal liability, waiver of right to sue or jury trial, auto-renewal with no exit, unilateral contract changes with no notice
- "medium" : discretionary language that favours the other party, non-competes under 1 year, salary reduction clauses, one-sided non-disparagement, vague termination-for-cause definitions
- "low"    : standard boilerplate present in most contracts — at-will employment, standard benefits, paid leave, governing law, confidentiality of business secrets, reasonable severance, dispute resolution in a named jurisdiction

Examples of "low": paid annual leave, health benefits, standard NDA, governing law clause, entire agreement clause.
Examples of "medium": annual salary review at company's sole discretion, 30-day notice for pay cuts, one-sided non-disparagement.
Examples of "high": all IP including personal projects assigned to company, 3-year worldwide non-compete, binding arbitration waiving class action rights."""

CLAUSE_HUMAN = "Analyze this contract clause:\n\n{clause}"

SUMMARY_SYSTEM = """You are a legal analyst. Read the clause risk summaries and return ONLY a valid JSON object — no explanation, no markdown, no extra text.

Required format:
{{
  "contract_type": "type of contract e.g. Employment Agreement",
  "one_liner": "one sentence describing what this contract does",
  "top_risks": ["risk 1", "risk 2", "risk 3"],
  "lawyer_questions": ["question 1", "question 2", "question 3"]
}}"""

SUMMARY_HUMAN = """Clause analyses:
{analyses}

Summarize the full document."""


# ── LLM builder ───────────────────────────────────────────────────────────────

def build_llm(base_url: str = "http://localhost:1234/v1", temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=base_url,
        api_key="lm-studio",
        model="local-model",
        temperature=temperature,
    )


# ── JSON extraction ────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict | None:
    """Robustly extract a JSON object from model output."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract the first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return None


# ── Per-clause analysis ────────────────────────────────────────────────────────

def analyze_clause(llm: ChatOpenAI, clause_text: str, index: int) -> AnalyzedClause:
    prompt = ChatPromptTemplate.from_messages([
        ("system", CLAUSE_SYSTEM),
        ("human", CLAUSE_HUMAN),
    ])
    chain = prompt | llm

    try:
        response = chain.invoke({"clause": clause_text})
        raw = extract_json(response.content)
        if raw is None:
            return AnalyzedClause(
                index=index, text=clause_text, analysis=None,
                error=f"Could not parse JSON from response: {response.content[:200]}"
            )
        # Normalize risk_level in case model returns uppercase or whitespace
        if "risk_level" in raw:
            raw["risk_level"] = raw["risk_level"].strip().lower()
        analysis = ClauseAnalysis(**raw)
        return AnalyzedClause(index=index, text=clause_text, analysis=analysis)
    except Exception as e:
        return AnalyzedClause(index=index, text=clause_text, analysis=None, error=str(e))


# ── Document summary ──────────────────────────────────────────────────────────

def get_document_summary(llm: ChatOpenAI, analyzed: list[AnalyzedClause]) -> DocumentSummary | None:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARY_SYSTEM),
        ("human", SUMMARY_HUMAN),
    ])
    chain = prompt | llm

    lines = [
        f"Clause {a.index + 1} [{a.analysis.risk_level.upper()}]: {a.analysis.risk_reason}"
        for a in analyzed if a.analysis
    ]

    if not lines:
        return None

    try:
        response = chain.invoke({"analyses": "\n".join(lines)})
        raw = extract_json(response.content)
        if raw is None:
            return None
        return DocumentSummary(**raw)
    except Exception:
        return None
