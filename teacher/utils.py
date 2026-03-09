from PyPDF2 import PdfReader
import docx
import io


def extract_text_from_file(file):

    name = file.name.lower()

    # ================= PDF =================
    if name.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""

        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

        return text


    # ================= DOCX =================
    if name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs)


    return ""
import re

def parse_guideline_rules(text):
    """
    Robust PDF guideline parser.

    Strategy:
    1. Split lines
    2. If a line is only a number → merge with next line
    3. Otherwise keep normally
    4. Return structured list of rules
    """

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    rules = []
    i = 0

    while i < len(lines):

        current = lines[i]

        # case: line contains ONLY number (PDF split)
        if re.fullmatch(r'\d+', current) and i + 1 < len(lines):
            merged = f"{current} {lines[i+1]}"
            rules.append(merged)
            i += 2
            continue

        # normal numbered line (e.g. 1. Formatting Rules)
        if re.match(r'^\d+', current):
            rules.append(current)

        i += 1

    return rules

# ======================================================
# RULE → STRUCTURED CONFIG CONVERTER
# Converts parsed rule lines into machine-readable dict
# ======================================================

def build_rule_config(rules):
    """
    Converts rule strings into structured config
    used later for automatic validation.
    """

    config = {}

    for rule in rules:

        r = rule.lower()

        # ---------------- FONT ----------------
        if "font" in r:
            # example: Font: Times New Roman, 12pt
            parts = rule.split(":")[-1].strip()

            if "," in parts:
                name, size = parts.split(",", 1)
                config["font_name"] = name.strip()
                config["font_size"] = int(
                    ''.join(filter(str.isdigit, size))
                )

        # ---------------- LINE SPACING ----------------
        elif "spacing" in r:
            # Line spacing: 1.5
            value = ''.join(c for c in r if c.isdigit() or c == '.')
            config["line_spacing"] = float(value)

        # ---------------- MARGINS ----------------
        elif "margin" in r:
            # Margins: 1 inch
            value = ''.join(c for c in r if c.isdigit() or c == '.')
            config["margin_inches"] = float(value)

        # ---------------- FILE FORMAT ----------------
        elif "pdf format only" in r:
            config["file_format"] = "pdf"

        # ---------------- FILE SIZE ----------------
        elif "file size" in r:
            value = ''.join(c for c in r if c.isdigit())
            config["max_size_mb"] = int(value)

        # ---------------- ATTEMPTS ----------------
        elif "attempt" in r:
            value = ''.join(c for c in r if c.isdigit())
            config["max_attempts"] = int(value)

    return config
