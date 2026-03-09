# =========================================================
# EduDOC – Plagiarism Engine (Step 14)
# Local similarity detection (no external APIs)
# =========================================================

import re
from typing import List, Dict, Tuple
from docx import Document
from PyPDF2 import PdfReader


# =========================================================
# TEXT EXTRACTION
# =========================================================
def extract_text(path: str) -> str:

    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return " ".join(page.extract_text() or "" for page in reader.pages)

    if path.lower().endswith(".docx"):
        doc = Document(path)
        return " ".join(p.text for p in doc.paragraphs)

    return ""


# =========================================================
# NORMALIZATION
# =========================================================
def normalize(text: str) -> str:

    text = text.lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# SHINGLING (n-gram phrases)
# =========================================================
def make_shingles(text: str, k: int = 6) -> set:

    words = text.split()

    return {
        " ".join(words[i:i+k])
        for i in range(len(words) - k + 1)
    }


# =========================================================
# JACCARD SIMILARITY
# =========================================================
def similarity(a: set, b: set) -> float:

    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


# =========================================================
# MAIN ENTRY
# =========================================================
def run_plagiarism_check(
    document_path: str,
    corpus_paths: List[str],
    threshold: float = 0.25
) -> Dict:
    """
    Compare document with institutional corpus.

    threshold = 0.25 → 25% similarity flagged
    """

    base_text = normalize(extract_text(document_path))
    base_shingles = make_shingles(base_text)

    max_similarity = 0
    matches: List[Tuple[str, float]] = []

    for other_path in corpus_paths:

        other_text = normalize(extract_text(other_path))
        other_shingles = make_shingles(other_text)

        sim = similarity(base_shingles, other_shingles)

        if sim > max_similarity:
            max_similarity = sim

        if sim >= threshold:
            matches.append((other_path, round(sim * 100, 2)))

    return {
        "plagiarism_percent": round(max_similarity * 100, 2),
        "matches": matches
    }
