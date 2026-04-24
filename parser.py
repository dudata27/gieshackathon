"""
parser.py
Parses the Copilot Studio agent's markdown response into structured scorecard fields.

The agent returns markdown that we need to convert into the dict format our
Streamlit render_scorecard function expects.
"""

import re
from typing import Optional


# Fields our render_scorecard function expects:
# posting_id, company_name, job_title, city, state, industry, company_size,
# funding_stage, posting_age_days, first_hire, first_hire_quote, first_hire_confidence,
# cluster, cluster_quote, cluster_confidence, new_initiative, new_initiative_quote,
# new_initiative_confidence, industry_fit, geography_fit, program_fit, final_score,
# tier, flagged, score_math (list of tuples), raw_total, rationale, recommended_owner


def _find_score(text: str) -> Optional[int]:
    """Extract the final score (0-100) from the response."""
    # Strip markdown asterisks for easier matching
    cleaned = text.replace("**", "").replace("__", "")

    patterns = [
        r"(?i)fit\s*score[:\s]*(\d{1,3})\s*/\s*100",
        r"(?i)fit\s*score[:\s]*(\d{1,3})",
        r"(?i)final\s*score[:\s]*(\d{1,3})",
        r"(?i)final[^a-z]*?(\d{1,3})\s*/\s*100",
        r"(?i)clipped\s*(?:to\s*)?(?:\d+[\-–]\d+[:\s]*)?(\d{1,3})\b",
        r"(?i)new\s*score[:\s]*(\d{1,3})",
        r"(?i)score[:\s]+(\d{1,3})(?:\s*/\s*100)",
        r"=\s*\d+\s*(?:→|->)\s*clipped\s*to\s*(\d{1,3})",
        r"(?i)^\s*score[:\s]+(\d{1,3})\s*$",
    ]
    for p in patterns:
        m = re.search(p, cleaned, re.MULTILINE)
        if m:
            val = int(m.group(1))
            if 18 <= val <= 100:  # must be within clipped range
                return val
    return None


def _find_tier(text: str) -> Optional[str]:
    """Extract tier letter (A/B/C/D)."""
    cleaned = text.replace("**", "").replace("__", "")
    patterns = [
        r"(?i)tier[:\s]+([ABCD])\b",
        r"(?i)new\s*tier[:\s]+([ABCD])\b",
    ]
    for p in patterns:
        m = re.search(p, cleaned)
        if m:
            return m.group(1).upper()
    return None


def _find_flagged(text: str) -> Optional[bool]:
    """Extract flagged status."""
    cleaned = text.replace("**", "").replace("__", "")
    # Negative patterns first (they're more specific)
    neg = [
        r"(?i)not\s*flagged",
        r"(?i)flagged[^\n]*[:\s]+no\b",
        r"(?i)outreach[:\s]+(?:not\s*flagged|no\b)",
        r"✗",
    ]
    for p in neg:
        if re.search(p, cleaned):
            return False
    # Positive patterns
    pos = [
        r"(?i)flagged\s*for\s*outreach",
        r"(?i)outreach[:\s]*flagged",
        r"(?i)flagged[:\s]*yes",
        r"✔|✓",
    ]
    for p in pos:
        if re.search(p, cleaned):
            return True
    return None


def _find_company(text: str) -> Optional[str]:
    """Extract company name."""
    lines = text.strip().split("\n")
    for line in lines[:20]:
        line = line.strip().lstrip("#").strip()
        if not line:
            continue
        # Skip separator lines (=====, ----, ....)
        if set(line) <= set("=-_. \t"):
            continue
        # Skip markdown table borders
        if line.startswith("|") and line.count("|") > 2:
            continue
        # Skip section headers
        if line.upper() in ("SIGNALS", "FIT BREAKDOWN", "SCORE MATH", "RATIONALE", "HEADER", "RECOMMENDED OWNER"):
            continue
        # Pattern: "**CompanyName** | RoleName" or "CompanyName | RoleName"
        clean_line = line.replace("**", "").replace("__", "").strip()
        if "|" in clean_line:
            part = clean_line.split("|")[0].strip()
            if part and len(part) < 80 and "score" not in part.lower() and "[" not in part:
                return part
        # Pattern: just "**CompanyName**" on its own line
        bold_match = re.match(r"^\*\*([^*]+)\*\*\s*$", line)
        if bold_match:
            candidate = bold_match.group(1).strip()
            if len(candidate) < 80 and "[" not in candidate:
                return candidate
    return None


def _find_role(text: str) -> Optional[str]:
    """Extract role title."""
    lines = text.strip().split("\n")
    for line in lines[:20]:
        line = line.strip().lstrip("#").strip()
        if not line:
            continue
        if set(line) <= set("=-_. \t"):
            continue
        clean_line = line.replace("**", "").replace("__", "").strip()
        if "|" in clean_line:
            parts = clean_line.split("|")
            if len(parts) >= 2:
                role = parts[1].strip()
                if role and len(role) < 120 and "[" not in role:
                    return role
    # Fallback: look for common titles
    titles = ["Head of", "Director of", "VP", "Chief", "Manager", "Lead"]
    for title in titles:
        m = re.search(rf"\b{title}\s+[A-Z][A-Za-z\s&,]+", text)
        if m:
            return m.group(0).strip().rstrip(".").rstrip(",")
    return None


def _find_location(text: str) -> tuple:
    """Extract (city, state)."""
    # Pattern: "City, ST" with 2-letter state code, within a single line only
    # Scan line by line for cleanest match
    for line in text.split("\n"):
        m = re.search(r"\b([A-Z][a-zA-Z\s\.'-]{1,30}?),\s*([A-Z]{2})\b", line)
        if m:
            city = m.group(1).strip()
            state = m.group(2).strip()
            # Skip false positives
            if city.lower() not in ("head of growth", "director of", "vp of", "chief of"):
                return city, state
    return "Unknown", "??"


def _find_industry(text: str) -> str:
    """Extract industry."""
    # Common patterns: "| HealthTech |" or "Industry: HealthTech"
    m = re.search(r"(?i)industry[:\s]*\**\s*([A-Za-z][A-Za-z\s&/]+?)(?:\n|\||[\.;])", text)
    if m:
        return m.group(1).strip()
    # Pipe-delimited pattern
    industries = ["HealthTech", "FinTech", "Logistics", "Retail", "SaaS", "Manufacturing", "Consumer Goods", "Energy", "EdTech"]
    for ind in industries:
        if re.search(rf"\b{re.escape(ind)}\b", text):
            return ind
    return "Unknown"


def _find_company_size(text: str) -> str:
    """Extract company size."""
    m = re.search(r"\b(\d+\+?|\d+[\-–]\d+)\s*employees?\b", text, re.IGNORECASE)
    if m:
        return m.group(1)
    sizes = ["1000+", "500-999", "200-499", "50-199", "11-50", "1-10"]
    for s in sizes:
        if s in text:
            return s
    return "Unknown"


def _find_funding(text: str) -> str:
    """Extract funding stage."""
    stages = ["Series A", "Series B", "Series C", "Series D", "Private Equity", "Seed", "Public", "Bootstrapped"]
    for s in stages:
        if re.search(rf"\b{re.escape(s)}\b", text, re.IGNORECASE):
            return s
    return "Unknown"


def _find_posting_age(text: str) -> int:
    """Extract posting age in days."""
    m = re.search(r"(\d+)\s*days?\s*(?:ago|old)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"posting\s*age[:\s]+\**\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def _extract_signal(text: str, signal_name: str) -> tuple:
    """
    Extract (value, quote, confidence) for a named signal.
    Handles markdown bold formatting: 'First strategic hire: **Yes** — High confidence'
    followed by 'Quote: "..."' on the next line.
    """
    # Strip markdown asterisks
    cleaned = text.replace("**", "")

    sig_aliases = {
        "First Strategic Hire": ["first strategic hire", "first.hire", "first dedicated"],
        "Cluster Hiring": ["cluster hiring", "cluster"],
        "New Initiative": ["new initiative", "initiative"],
    }
    aliases = sig_aliases.get(signal_name, [signal_name.lower()])

    for alias in aliases:
        # Match: "<alias>: Yes — High confidence" then optionally a quote
        # Use re.IGNORECASE | re.DOTALL, stop at next blank line or next signal
        pattern = (
            rf"(?is)\b{alias}\s*[:\-]?\s*"             # header
            rf"(Yes|No)\s*"                            # value
            rf"[^\n]*?"                                # dash/em-dash filler
            rf"(High|Medium|Low)?\s*confidence?"       # optional confidence
            rf"(.*?)"                                  # body with quote
            rf"(?=\n\s*(?:Cluster|New\s*initiative|Industry\s*fit|Fit|FIT|Score|SCORE|Tier|TIER|Rationale|RATIONALE|Recommended|RECOMMENDED|\Z))"
        )
        m = re.search(pattern, cleaned)
        if m:
            value = m.group(1).capitalize()
            confidence = (m.group(2) or "High").capitalize()
            body = m.group(3) or ""
            quote = _extract_quote(body)
            return value, quote, confidence
    return "No", "", "Medium"


def _extract_quote(text: str) -> str:
    """Find a quoted passage in the text."""
    # Try quote patterns in order
    patterns = [
        r'Quote\s*:\s*"([^"]{10,800})"',   # "Quote: "...""
        r'"([^"]{20,800})"',                # plain double quotes
        r'"([^"]{20,800})"',                # smart quotes
        r'>\s*([^\n]{20,800})',             # blockquote
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return ""


def _find_fit(text: str, axis: str, default: str) -> str:
    """Extract fit rating for axis (industry/geography/program)."""
    if axis == "industry":
        m = re.search(r"(?i)industry\s*fit[:\s]*\**\s*(High|Medium|Low)\b", text)
        return m.group(1).capitalize() if m else default
    if axis == "geography":
        if re.search(r"(?i)geography\s*fit[:\s]*\**\s*(No|\bN\b)", text):
            return "No"
        if re.search(r"(?i)geography\s*fit[:\s]*\**\s*(Yes|\bY\b)", text):
            return "Yes"
        return default
    if axis == "program":
        m = re.search(r"(?i)program\s*fit[:\s]*\**\s*(Strong|Moderate|Weak)\b", text)
        return m.group(1).capitalize() if m else default
    return default


def _extract_math(text: str) -> tuple:
    """Extract score math components and raw total."""
    cleaned = text.replace("**", "").replace("__", "")
    rows = []
    raw_total = 0

    # Component-wise extraction: grab the FIRST signed number after the label,
    # not crossing past another component keyword.
    # Each pattern: <label> ... <possibly sign><digits> ... before next keyword
    candidates = [
        ("Baseline", r"baseline\s*\+?(\d{1,2})"),
        ("First strategic hire", r"first(?:\s*strategic)?\s*hire(?:[^+\-]{0,15})([+\-]\d{1,2}|\b\d{1,2}\b)"),
        ("Cluster hiring", r"cluster(?:\s*hiring)?(?:[^+\-]{0,15})([+\-]\d{1,2}|\b\d{1,2}\b)"),
        ("New initiative", r"new\s*initiative(?:[^+\-]{0,15})([+\-]\d{1,2}|\b\d{1,2}\b)"),
        ("Industry fit", r"industry(?:[^+\-]{0,25})([+\-]\d{1,2}|\b\d{1,2}\b)"),
        ("Geography fit", r"geography(?:[^+\-]{0,25})([+\-]\d{1,2}|\b\d{1,2}\b)"),
        ("Program fit", r"program(?:[^+\-]{0,25})([+\-]\d{1,2}|\b\d{1,2}\b)"),
        ("Age decay", r"age\s*decay\s*([+\-]?\d{1,2})(?=\s|$|=|\+)"),
    ]

    for label, pattern in candidates:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            raw_val = m.group(1).strip()
            if raw_val.startswith("+"):
                raw_val = raw_val[1:]
            try:
                val = int(raw_val)
                # Sanity: baseline is 22, most others 0-19. If we got 22 for non-baseline, skip
                if label != "Baseline" and val == 22:
                    continue
                rows.append((label, val))
                raw_total += val
            except ValueError:
                pass

    # Prefer explicit "Raw total: N" if present
    m = re.search(r"(?i)raw\s*total[:\s]+\+?(\d+)", cleaned)
    if m:
        raw_total = int(m.group(1))
    else:
        # Fall back to "= N" or "= N → clipped" pattern
        m = re.search(r"=\s*\+?(\d+)\s*(?:→|->)", cleaned)
        if m:
            raw_total = int(m.group(1))

    return rows, raw_total


def _extract_rationale(text: str) -> str:
    """Extract rationale block."""
    cleaned = text.replace("**", "")
    # Match Rationale section: header line, then body until Recommended Owner or end
    m = re.search(
        r"(?is)rationale\s*\n+(.*?)(?=\n\s*(?:recommended|owner|\Z))",
        cleaned,
    )
    if m:
        rat = m.group(1).strip()
        # Take first 2 sentences max
        sentences = re.split(r'(?<=[.!?])\s+', rat)
        return " ".join(sentences[:2])
    # Fallback: single-line "RATIONALE: ..." pattern
    m = re.search(r"(?i)rationale[:\s]+([^\n]{20,600})", cleaned)
    if m:
        return m.group(1).strip()
    return "Scored against Magelli consulting-fit rubric."


def parse_scorecard(posting_id: str, agent_text: str) -> dict:
    """
    Parse the agent's markdown response into a scorecard dict that
    render_scorecard() can consume.
    """
    score = _find_score(agent_text) or 0
    tier = _find_tier(agent_text) or ("A" if score >= 82 else "B" if score >= 69 else "C" if score >= 55 else "D")
    flagged = _find_flagged(agent_text)
    if flagged is None:
        flagged = score >= 69  # fallback heuristic

    city, state = _find_location(agent_text)

    # Geography hard filter — override flagged based on state
    midwest_states = {"IL", "WI", "IN", "IA", "MN", "OH", "MI", "MO"}
    if state not in midwest_states:
        flagged = False

    fh_val, fh_quote, fh_conf = _extract_signal(agent_text, "First Strategic Hire")
    cl_val, cl_quote, cl_conf = _extract_signal(agent_text, "Cluster Hiring")
    ni_val, ni_quote, ni_conf = _extract_signal(agent_text, "New Initiative")

    math_rows, raw_total = _extract_math(agent_text)

    return {
        "posting_id": posting_id.upper(),
        "company_name": _find_company(agent_text) or "Unknown Company",
        "job_title": _find_role(agent_text) or "Unknown Role",
        "city": city,
        "state": state,
        "industry": _find_industry(agent_text),
        "company_size": _find_company_size(agent_text),
        "funding_stage": _find_funding(agent_text),
        "posting_age_days": _find_posting_age(agent_text),
        "first_hire": fh_val,
        "first_hire_quote": fh_quote,
        "first_hire_confidence": fh_conf,
        "cluster": cl_val,
        "cluster_quote": cl_quote,
        "cluster_confidence": cl_conf,
        "new_initiative": ni_val,
        "new_initiative_quote": ni_quote,
        "new_initiative_confidence": ni_conf,
        "industry_fit": _find_fit(agent_text, "industry", "Medium"),
        "geography_fit": _find_fit(agent_text, "geography", "Yes" if state in midwest_states else "No"),
        "program_fit": _find_fit(agent_text, "program", "Moderate"),
        "final_score": score,
        "tier": tier,
        "flagged": flagged,
        "score_math": math_rows,
        "raw_total": raw_total,
        "rationale": _extract_rationale(agent_text),
        "recommended_owner": _recommended_owner(flagged, tier, state in midwest_states),
        "raw_response": agent_text,  # keep for display fallback
    }


def _recommended_owner(flagged: bool, tier: str, in_midwest: bool) -> str:
    if not flagged:
        if not in_midwest:
            return "Not flagged - geography outside IL/WI/IN/IA/MN/OH/MI/MO target region"
        return "Not flagged - score below outreach threshold"
    if tier == "A":
        return "Senior faculty advisor - contact this week"
    if tier == "B":
        return "Associate faculty - contact within 2 weeks"
    return "Queue for next sourcing review"


if __name__ == "__main__":
    # Smoke test with the BT-024 response we saw earlier
    sample = """NorthStack Partners | Head of Growth
Peoria, IL | HealthTech | 1000+ employees | Private Equity | Posting age: 2 days

1. Signal-by-Signal Breakdown
First Strategic Hire: Yes — High confidence
"Following recent investment, we are formalizing our growth function and this is the first dedicated leader for the team. You will establish the growth function, build the playbook, and set the operating cadence."

+19 points

Cluster Hiring: Yes — High confidence
"As we scale the team, we are building out several adjacent functions in parallel."

+16 points

New Initiative: Yes — High confidence
"In the next two quarters we are migrating our patient data platform to Snowflake, and this role will partner closely on that initiative."

+14 points

2. Fit Assessment
Industry fit: High +14 points
Geography fit: Yes +8 points
Program fit: Strong +11 points

3. Score Math
Baseline: 22
Raw total: 104
Clipped to 18-98: 98

4. Tier & Outreach Status
Tier: A
Flagged for outreach: Yes

5. Rationale
BT-024 earned the maximum clipped score of 98 because all three growth signals fired at High confidence.
"""
    result = parse_scorecard("BT-024", sample)
    import json
    print(json.dumps({k: v for k, v in result.items() if k != "raw_response"}, indent=2, default=str))
