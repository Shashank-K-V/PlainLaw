from pydantic import BaseModel
from typing import Literal


class ClauseAnalysis(BaseModel):
    risk_level: Literal["high", "medium", "low"]
    risk_reason: str          # one sentence: why this is risky (or not)
    plain_english: str        # 2-3 sentence plain English explanation
    tags: list[str]           # e.g. ["IP assignment", "non-compete", "termination"]
    questions: list[str]      # questions to ask a lawyer about this clause


class DocumentSummary(BaseModel):
    contract_type: str        # e.g. "Employment Agreement", "NDA", "Lease"
    one_liner: str            # one sentence describing what this contract does
    top_risks: list[str]      # top 3 risks in the document
    lawyer_questions: list[str]  # top 3 questions to ask before signing


class AnalyzedClause(BaseModel):
    index: int
    text: str
    analysis: ClauseAnalysis | None
    error: str | None = None
