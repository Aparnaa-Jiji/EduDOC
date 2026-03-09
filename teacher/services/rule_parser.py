# =========================================================
# RULE PARSER SERVICE — EduDOC
# Deterministic • Teacher Assisted • Safe Automation
# =========================================================

import re
from docx import Document
from pathlib import Path
from docx import Document
import pdfplumber

class RuleParser:
    """
    Parses guideline documents and extracts
    compliance rules automatically.

    NOTE:
    Automation NEVER locks rules.
    Teacher review is mandatory.
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.text = ""

    # -----------------------------------------------------
    # Load Document
    # -----------------------------------------------------



    def load_document(self):

        file_ext = Path(self.file_path).suffix.lower()

        # ===============================
        # DOCX SUPPORT
        # ===============================
        if file_ext == ".docx":
            doc = Document(self.file_path)
            self.text = "\n".join(p.text for p in doc.paragraphs)

        # ===============================
        # PDF SUPPORT
        # ===============================
        elif file_ext == ".pdf":
            text = []

            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)

            self.text = "\n".join(text)

        # ===============================
        # UNSUPPORTED TYPE
        # ===============================
        else:
            raise ValueError("Unsupported guideline format.")


    # -----------------------------------------------------
    # Extract Rules
    # -----------------------------------------------------
    def extract_rules(self):

        rules = {}
        text = self.text

        def find(label):
            import re
            pattern = rf"{label}\s*:\s*(.+)"
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else None

        rules["min_pages"] = find("Minimum Pages")
        rules["max_pages"] = find("Maximum Pages")
        rules["paper_size"] = find("Paper Size")

        rules["font_name"] = find("Font Name")
        rules["font_size"] = find("Font Size")
        rules["line_spacing"] = find("Line Spacing")

        rules["margin_top"] = find("Top Margin")
        rules["margin_bottom"] = find("Bottom Margin")
        rules["margin_left"] = find("Left Margin")
        rules["margin_right"] = find("Right Margin")

        return rules


    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------
    def parse(self):
        self.load_document()
        return self.extract_rules()
