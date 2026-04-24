"""
file_handler.py
Extracts job posting text from uploaded files.
Supports: xlsx, csv, pdf, docx, txt, md
"""

import io
from typing import List, Optional, Tuple

import pandas as pd


def extract_from_xlsx(file_bytes: bytes) -> List[dict]:
    """
    Parse xlsx into a list of posting dicts.
    Looks for columns like posting_id, company, title, city, state, description.
    Returns list of {id, label, text} where text is the full row serialized as context.
    """
    bio = io.BytesIO(file_bytes)
    try:
        df = pd.read_excel(bio, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Could not read xlsx: {e}")
    return _rows_from_df(df)


def extract_from_csv(file_bytes: bytes) -> List[dict]:
    """Parse csv into posting dicts."""
    bio = io.BytesIO(file_bytes)
    try:
        df = pd.read_csv(bio)
    except Exception as e:
        # Try different encodings
        bio.seek(0)
        try:
            df = pd.read_csv(bio, encoding="latin-1")
        except Exception as e2:
            raise ValueError(f"Could not read csv: {e}")
    return _rows_from_df(df)


def _rows_from_df(df: pd.DataFrame) -> List[dict]:
    """Convert a dataframe of postings into our standard format."""
    postings = []
    cols = {c.lower().strip(): c for c in df.columns}

    id_col = _pick_col(cols, ["posting_id", "id", "posting id", "posting", "bt", "bt-id"])
    company_col = _pick_col(cols, ["company_name", "company", "organization", "employer"])
    title_col = _pick_col(cols, ["job_title", "title", "role", "position"])
    city_col = _pick_col(cols, ["city"])
    state_col = _pick_col(cols, ["state", "st", "region"])
    desc_col = _pick_col(cols, ["description", "posting_text", "body", "content", "details"])

    for idx, row in df.iterrows():
        pid = _safe_str(row.get(id_col)) if id_col else f"ROW-{idx+1}"
        company = _safe_str(row.get(company_col)) if company_col else "Unknown"
        title = _safe_str(row.get(title_col)) if title_col else ""
        city = _safe_str(row.get(city_col)) if city_col else ""
        state = _safe_str(row.get(state_col)) if state_col else ""
        desc = _safe_str(row.get(desc_col)) if desc_col else ""

        # Build a label for the dropdown
        label_parts = [pid]
        if company and company != "Unknown":
            label_parts.append(company)
        if title:
            label_parts.append(title)
        if city and state:
            label_parts.append(f"{city}, {state}")
        label = " — ".join(label_parts)

        # Build full text representation (all columns, comma-joined)
        text_parts = []
        for col in df.columns:
            val = _safe_str(row.get(col))
            if val:
                text_parts.append(f"{col}: {val}")
        text = "\n".join(text_parts)

        postings.append({"id": pid, "label": label, "text": text})

    return postings


def _pick_col(cols_lower: dict, candidates: List[str]) -> Optional[str]:
    """Find the first matching column name (case-insensitive)."""
    for c in candidates:
        if c in cols_lower:
            return cols_lower[c]
    # Partial match fallback
    for c in candidates:
        for lc, orig in cols_lower.items():
            if c in lc:
                return orig
    return None


def _safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract text from pdf. Requires pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support requires pypdf. Add 'pypdf' to requirements.txt")
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip()


def extract_from_docx(file_bytes: bytes) -> str:
    """Extract text from docx. Requires python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ValueError("DOCX support requires python-docx. Add 'python-docx' to requirements.txt")
    doc = Document(io.BytesIO(file_bytes))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_from_txt(file_bytes: bytes) -> str:
    """Extract from plain text / markdown."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def process_uploaded_file(file_name: str, file_bytes: bytes):
    """
    Route the uploaded file to the right extractor.
    Returns either:
        {"mode": "multi", "postings": [list of posting dicts]}  for xlsx/csv
        {"mode": "single", "text": "..."}                        for pdf/docx/txt
    """
    name = file_name.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return {"mode": "multi", "postings": extract_from_xlsx(file_bytes)}
    if name.endswith(".csv"):
        return {"mode": "multi", "postings": extract_from_csv(file_bytes)}
    if name.endswith(".pdf"):
        return {"mode": "single", "text": extract_from_pdf(file_bytes)}
    if name.endswith(".docx"):
        return {"mode": "single", "text": extract_from_docx(file_bytes)}
    if name.endswith((".txt", ".md")):
        return {"mode": "single", "text": extract_from_txt(file_bytes)}
    raise ValueError(f"Unsupported file type: {file_name}")


def truncate_text(text: str, max_chars: int = 4000) -> str:
    """Truncate text to safe size for Direct Line payloads."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated]"


if __name__ == "__main__":
    # Smoke test
    csv_data = b"""posting_id,company_name,job_title,city,state,description
BT-001,TestCorp,Head of Growth,Chicago,IL,"First dedicated growth leader. Cluster hiring."
BT-002,Example Inc,Director RevOps,Madison,WI,"Building new revenue function from scratch."
"""
    result = process_uploaded_file("test.csv", csv_data)
    print("Mode:", result["mode"])
    for p in result["postings"]:
        print(f"  {p['label']}")
        print(f"    text_preview: {p['text'][:80]}...")
