import re
import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def extract_clause_title(text: str) -> str | None:
    """Pull the heading out of a clause, e.g. '3. INTELLECTUAL PROPERTY ASSIGNMENT'."""
    text = text.strip()
    # Numbered + ALLCAPS heading on same or next line
    match = re.match(r'^\d+[\.\d]*\.?\s+([A-Z][A-Z &/\-]+)', text)
    if match:
        title = match.group(1).strip().rstrip('.')
        return title.title()  # Convert "NON-COMPETE RESTRICTION" → "Non-Compete Restriction"
    # First line if it looks like a heading (short, mostly uppercase)
    first_line = text.split('\n')[0].strip()[:80]
    if first_line and first_line == first_line.upper() and len(first_line) > 4:
        return first_line.title()
    return None


def split_into_clauses(text: str, max_clauses: int = 40) -> list[str]:
    """
    Split contract text into individual clauses.
    Strategy: numbered sections first, then paragraph fallback.
    """
    # Normalize whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Try splitting on numbered sections (e.g. "1.", "1.1", "Section 1", "Article 1")
    numbered = re.split(
        r'\n(?=(?:\d+\.(?:\d+\.?)*\s+[A-Z]|Section\s+\d+|Article\s+\d+|SECTION\s+\d+|ARTICLE\s+\d+))',
        text
    )

    if len(numbered) >= 4:
        clauses = [c.strip() for c in numbered if c.strip()]
    else:
        # Fallback: split on double newlines (paragraph-based)
        clauses = [c.strip() for c in re.split(r'\n\s*\n', text) if c.strip()]

    # Merge very short fragments into the previous clause
    merged: list[str] = []
    for clause in clauses:
        if len(clause) < 60 and merged:
            merged[-1] = merged[-1] + " " + clause
        else:
            merged.append(clause)

    # Split any single clause that is too long (>1800 chars) on sub-numbering
    final: list[str] = []
    for clause in merged:
        if len(clause) > 1800:
            sub = re.split(r'(?<=\n)(?=\([a-zA-Z]\)\s|\([ivxlIVXL]+\)\s|\d+\)\s)', clause)
            for s in sub:
                s = s.strip()
                if len(s) > 60:
                    final.append(s)
        else:
            final.append(clause)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in final:
        key = c[:80]
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique[:max_clauses]
