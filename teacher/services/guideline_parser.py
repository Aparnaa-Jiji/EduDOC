# =========================================================
# EduDOC TEMPLATE PARSER (Deterministic)
# Parses: key = value lines only
# NO regex • NO AI • 100% reliable
# =========================================================

import pdfplumber
from pathlib import Path
from typing import Dict


class GuidelineParser:

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path


    # -----------------------------------------------------
    # Extract raw text from PDF
    # -----------------------------------------------------
    def extract_text(self) -> str:

        path = Path(self.pdf_path)

        if not path.exists():
            return ""

        chunks = []

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    chunks.append(t)

        return "\n".join(chunks)


    # -----------------------------------------------------
    # NEW: KEY=VALUE PARSER
    # -----------------------------------------------------
    def parse_key_value_rules(self, text: str) -> Dict:

        rules = {}

        for line in text.splitlines():

            line = line.strip()

            # ignore empty / comments / headers
            if not line or line.startswith("[") or "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            # type conversion
            if value.isdigit():
                value = int(value)

            elif value.lower() in ["true", "false"]:
                value = value.lower() == "true"

            rules[key] = value

        return rules


    # -----------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------
    def get_rules(self) -> Dict:

        text = self.extract_text()

        if not text:
            return {}

        return self.parse_key_value_rules(text)
