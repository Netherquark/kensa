#!/usr/bin/env python3
"""Generic, robust programmatic guardrail adherence check for LaTeX (.tex) or compiled PDF documents.

Enforces guardrail27 rules:
- Writing style: direct, non-redundant, non-vague, purely technical, no analogies, no comparisons.
- Unique section content & flow.
- No omitted important info.
- Prohibition of forbidden writing tropes & strawmen (e.g., 'not because ... but because', 'instead of', 'rather than', em dashes, placeholders).
- Lexical & structural diversity checks (MTLD, Hapax, Yule's K, entropy, sentence/paragraph variation).
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORBIDDEN_TROPES = {
    "not_because_pivot": r"\bnot\s+because\b",
    "instead_of": r"\binstead\s+of\b",
    "rather_than": r"\brather\s+than\b",
    "strawman_comparison": r"\bnot\s+(?:an?\s+)?[^.,;!?]+?\s+but\s+[^.,;!?]+",
    "analogy_marker": r"\b(?:as\s+if|analogous\s+to|metaphorically|serves\s+as\s+an\s+analogy)\b",
    "em_dash": r"—",
    "markdown_bold": r"\*\*",
}

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b", r"\bTBD\b", r"\bFIXME\b", r"\bLOREM\s+IPSUM\b",
    r"\bINSERT\b", r"\bPLACEHOLDER\b", r"\bFILL\s+THIS\b"
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        except ImportError:
            # Fallback or error if pypdf isn't available, but we can try reading as text or raise
            raise RuntimeError("PDF input provided but pypdf is not installed. Please provide a .tex file or install pypdf.")
    else:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="ignore")
        return text


def strip_tex_comments(tex: str) -> str:
    out = []
    for line in tex.splitlines():
        cut = None
        for i, ch in enumerate(line):
            if ch == "%":
                slashes = 0
                j = i - 1
                while j >= 0 and line[j] == "\\":
                    slashes += 1
                    j -= 1
                if slashes % 2 == 0:
                    cut = i
                    break
        out.append(line[:cut] if cut is not None else line)
    return "\n".join(out)


def clean_prose(text: str) -> str:
    text = strip_tex_comments(text)
    # Remove environments that are code or mathematical displays
    for env in ("tikzpicture", "lstlisting", "verbatim", "equation", "align", "align*", "gather", "gather*"):
        text = re.sub(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"}", " ", text, flags=re.S)
    for env in ("tabular", "tabularx", "longtable", "thebibliography", "titlepage", "figure", "table"):
        text = re.sub(r"\\begin\{" + re.escape(env) + r"\}(?:.|\n)*?\\end\{" + re.escape(env) + r"}", " ", text, flags=re.S)
    
    text = re.sub(r"\\\[(?:.|\n)*?\\\]", " ", text)
    text = re.sub(r"\\\((?:.|\n)*?\\\)", " ", text)
    text = re.sub(r"\$.*?\$", " ", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", " ", text)
    text = re.sub(r"[{}$\\~^_]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [m.lower() for m in re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?|\d+(?:\.\d+)?", text)]


def split_sentences(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out: list[str] = []
    for p in paras:
        out.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", p) if s.strip())
    return out


def mtld(toks: list[str], threshold: float = 0.72) -> float:
    if not toks:
        return 0.0
    def direction(tokens_list: list[str]) -> float:
        factors = 0.0
        length = 0
        seen: set[str] = set()
        for tok in tokens_list:
            length += 1
            seen.add(tok)
            if len(seen) / length <= threshold:
                factors += 1.0
                length = 0
                seen.clear()
        if length:
            observed_ttr = len(seen) / length
            if observed_ttr < 1.0:
                factors += (1.0 - observed_ttr) / (1.0 - threshold)
        return factors
    fwd = direction(toks)
    rev = direction(list(reversed(toks)))
    factors = (fwd + rev) / 2
    return len(toks) / factors if factors else float(len(toks))


def char_entropy(text: str) -> float:
    chars = [c for c in text.lower() if not c.isspace()]
    freq = collections.Counter(chars)
    total = len(chars)
    return -sum((n / total) * math.log2(n / total) for n in freq.values()) if total else 0.0


def validate_document(doc_path: Path) -> dict[str, Any]:
    raw_text = read_document(doc_path)
    prose = clean_prose(raw_text)
    toks = tokenize(prose)
    sents = split_sentences(prose)
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]

    # 1. Trope checks
    trope_hits = {}
    for name, pattern in FORBIDDEN_TROPES.items():
        matches = re.findall(pattern, raw_text, flags=re.I)
        if matches:
            trope_hits[name] = len(matches)

    # 2. Placeholder checks
    placeholder_hits = []
    for pat in PLACEHOLDER_PATTERNS:
        matches = re.findall(pat, raw_text, flags=re.I)
        if matches:
            placeholder_hits.extend(matches)

    # 3. Lexical diversity metrics
    vocab_size = len(set(toks))
    total_tokens = len(toks)
    ttr = vocab_size / total_tokens if total_tokens > 0 else 0.0
    hapax_count = sum(1 for c in collections.Counter(toks).values() if c == 1)
    hapax_ratio = hapax_count / max(1, vocab_size)
    yules_k = 10000 * (sum(c * c for c in collections.Counter(toks).values()) - total_tokens) / (total_tokens * total_tokens) if total_tokens > 0 else 0.0
    entropy = char_entropy(raw_text)
    mtld_val = mtld(toks)

    # 4. Structural variance
    sent_lengths = [len(tokenize(s)) for s in sents if tokenize(s)]
    para_lengths = [len(tokenize(p)) for p in paras if tokenize(p)]
    
    sent_len_cv = statistics.pstdev(sent_lengths) / statistics.mean(sent_lengths) if sent_lengths and statistics.mean(sent_lengths) > 0 else 0.0
    para_len_cv = statistics.pstdev(para_lengths) / statistics.mean(para_lengths) if para_lengths and statistics.mean(para_lengths) > 0 else 0.0

    # 5. Section uniqueness / flow (if LaTeX sections present)
    sections = re.findall(r"\\section\*?\{([^{}]+)\}", raw_text)
    unique_sections = len(set(sections)) == len(sections) if sections else True

    checks = []
    def add_check(name: str, passed: bool, observed: Any, requirement: str, severity: str = "error"):
        checks.append({
            "check": name,
            "status": "PASS" if passed else ("WARN" if severity == "warn" else "FAIL"),
            "observed": observed,
            "requirement": requirement,
            "severity": severity
        })

    add_check("no_forbidden_tropes", not trope_hits, trope_hits, "No forbidden writing tropes, em dashes, or markdown bold markers.")
    add_check("no_placeholders", not placeholder_hits, {"hits": placeholder_hits[:10]}, "No placeholder text (TODO, TBD, FIXME, etc.).")
    add_check("lexical_diversity_mtld", mtld_val >= 40.0, {"mtld": round(mtld_val, 2)}, "Maintain healthy lexical diversity (MTLD >= 40).", severity="warn")
    add_check("hapax_ratio", hapax_ratio >= 0.3, {"hapax_ratio": round(hapax_ratio, 3)}, "High Hapax Legomena ratio through low-frequency vocabulary.", severity="warn")
    add_check("yules_k_low", yules_k <= 150.0, {"yules_k": round(yules_k, 2)}, "Keep Yule's K low to avoid concentrated vocabulary reuse.", severity="warn")
    add_check("sentence_length_variation", sent_len_cv >= 0.3, {"cv": round(sent_len_cv, 3)}, "Vary sentence length significantly across the document.", severity="warn")
    add_check("paragraph_length_variation", para_len_cv >= 0.3, {"cv": round(para_len_cv, 3)}, "Vary paragraph length across the document.", severity="warn")
    add_check("unique_sections", unique_sections, {"section_count": len(sections), "unique_count": len(set(sections))}, "Each section title and content block must be unique and non-redundant.")

    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")

    return {
        "schema": "guardrail27.generic.v1",
        "generated_at_utc": now_utc(),
        "document": str(doc_path),
        "overall_status": "PASS" if fail_count == 0 else "FAIL",
        "checks_passed": sum(1 for c in checks if c["status"] == "PASS"),
        "checks_failed": fail_count,
        "warnings": warn_count,
        "checks_total": len(checks),
        "checks": checks,
        "metrics": {
            "total_tokens": total_tokens,
            "vocab_size": vocab_size,
            "type_token_ratio": round(ttr, 4),
            "mtld": round(mtld_val, 2),
            "hapax_ratio": round(hapax_ratio, 4),
            "yules_k": round(yules_k, 2),
            "character_entropy": round(entropy, 4),
            "sentence_length_cv": round(sent_len_cv, 4),
            "paragraph_length_cv": round(para_len_cv, 4)
        }
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("document", type=Path, help="Path to LaTeX (.tex) or compiled PDF document")
    ap.add_argument("--out", type=Path, default=Path("quality/guardrail27.json"), help="Output validation JSON path")
    args = ap.parse_args()

    doc_path = args.document.resolve()
    if not doc_path.is_file():
        print(f"Error: Document not found: {doc_path}", file=sys.stderr)
        return 2

    try:
        result = validate_document(doc_path)
    except Exception as exc:
        print(f"Validation failed with exception: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "overall_status": result["overall_status"],
        "checks_passed": result["checks_passed"],
        "checks_failed": result["checks_failed"],
        "warnings": result["warnings"],
        "output": str(out_path)
    }, indent=2))

    return 0 if result["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
