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
    Robust to header rows being in row 1 or row 2, merged title cells, etc.
    """
    bio = io.BytesIO(file_bytes)
    try:
        df = pd.read_excel(bio, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Could not read xlsx: {e}")

    # If the first row looks like a subtitle rather than column headers
    # (e.g. 'Magelli Prospects Week of...'), re-read using row 1 as header
    df = _fix_header_if_needed(df, bio)
    return _rows_from_df(df)


def _fix_header_if_needed(df: pd.DataFrame, bio: io.BytesIO) -> pd.DataFrame:
    """
    If pandas picked up a title row instead of real column headers,
    try reading again with header=1.
    """
    col_names_lower = [str(c).lower().strip() for c in df.columns]

    # Signs the first row is NOT real headers:
    # - Unnamed columns (pandas fallback)
    # - All NaN in one row
    # - A column named like 'magelli' or 'prospects' (subtitle text)
    unnamed_count = sum(1 for c in col_names_lower if c.startswith("unnamed"))
    title_keywords = ["magelli", "prospect", "batch", "week of", "report"]
    has_title_word = any(any(kw in c for kw in title_keywords) for c in col_names_lower)

    if unnamed_count >= 2 or has_title_word:
        bio.seek(0)
        try:
            df2 = pd.read_excel(bio, engine="openpyxl", header=1)
            # Sanity check: must have recognizable content columns
            if any("posting" in str(c).lower() or "company" in str(c).lower() or "title" in str(c).lower() for c in df2.columns):
                return df2
        except Exception:
            pass

    return df


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
    # Drop rows that are entirely NaN (stray blank rows)
    df = df.dropna(how="all").reset_index(drop=True)

    postings = []
    # Normalize column names for matching (lowercase, strip, remove punctuation)
    cols_normalized = {_normalize_col(c): c for c in df.columns}

    id_col = _pick_col(cols_normalized, [
        "postingid", "posting id", "id", "posting", "postid", "bt", "btid", "bt-id",
        "jobid", "job id", "jobpostingid",
    ])
    company_col = _pick_col(cols_normalized, [
        "companyname", "company name", "company", "organization", "employer",
        "firm", "business",
    ])
    title_col = _pick_col(cols_normalized, [
        "jobtitle", "job title", "title", "role", "position", "roletitle",
    ])
    city_col = _pick_col(cols_normalized, ["city", "location city"])
    state_col = _pick_col(cols_normalized, ["state", "st", "region", "locationstate"])
    industry_col = _pick_col(cols_normalized, ["industry", "sector", "vertical"])
    size_col = _pick_col(cols_normalized, [
        "companysize", "company size", "size", "employees", "headcount",
    ])
    funding_col = _pick_col(cols_normalized, [
        "fundingstage", "funding stage", "funding", "stage", "capitalization",
    ])
    age_col = _pick_col(cols_normalized, [
        "postingage", "posting age", "age", "daysposted", "days posted",
        "postingagedays", "dayssinceposted",
    ])
    desc_col = _pick_col(cols_normalized, [
        "description", "posting text", "postingtext", "body", "content",
        "details", "postingbody", "jobdescription", "job description",
        "text", "full text", "fulltext", "post",
    ])

    for idx, row in df.iterrows():
        pid = _safe_str(row.get(id_col)) if id_col else f"ROW-{idx+1}"
        if not pid:
            pid = f"ROW-{idx+1}"
        company = _safe_str(row.get(company_col)) if company_col else ""
        title = _safe_str(row.get(title_col)) if title_col else ""
        city = _safe_str(row.get(city_col)) if city_col else ""
        state = _safe_str(row.get(state_col)) if state_col else ""
        desc = _safe_str(row.get(desc_col)) if desc_col else ""

        # Build a label for the dropdown
        label_parts = [pid]
        if company:
            label_parts.append(company)
        if title:
            label_parts.append(title)
        if city and state:
            label_parts.append(f"{city}, {state}")
        elif city or state:
            label_parts.append(city or state)
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


def _normalize_col(name) -> str:
    """Lowercase, strip whitespace, remove punctuation for fuzzy matching."""
    if name is None:
        return ""
    s = str(name).lower().strip()
    # Remove common separators
    for ch in [" ", "_", "-", ".", "(", ")", "/"]:
        s = s.replace(ch, "")
    return s


def _pick_col(cols_normalized: dict, candidates: List[str]) -> Optional[str]:
    """Find the first matching column name using normalized keys."""
    normalized_candidates = [_normalize_col(c) for c in candidates]
    # Exact match first
    for c in normalized_candidates:
        if c in cols_normalized:
            return cols_normalized[c]
    # Partial match fallback
    for c in normalized_candidates:
        for normalized_key, original in cols_normalized.items():
            if c and c in normalized_key:
                return original
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
