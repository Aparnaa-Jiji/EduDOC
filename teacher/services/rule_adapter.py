# =====================================================
# RULE ADAPTER
# Parser Output → ManualComplianceForm Initial Data
# =====================================================

def adapt_rules_to_form(parsed):

    if not parsed:
        return {}

    form_data = {}

    # ---------------------------
    # PAGE RULES
    # ---------------------------
    page = parsed.get("page_rules", {})
    form_data["min_pages"] = page.get("min_pages")
    form_data["max_pages"] = page.get("max_pages")
    form_data["paper_size"] = page.get("paper_size")

    # ---------------------------
    # MARGINS (stored internally in inches)
    # ---------------------------
    margins = parsed.get("margins", {})

    form_data["margin_top"] = margins.get("top")
    form_data["margin_bottom"] = margins.get("bottom")
    form_data["margin_left"] = margins.get("left")
    form_data["margin_right"] = margins.get("right")

    # assume inches detected
    form_data["margin_unit"] = "inch"

    # ---------------------------
    # FONT RULES
    # ---------------------------
    font = parsed.get("font_rules", {})

    form_data["font_name"] = font.get("font_name")
    form_data["font_color"] = font.get("font_color")
    form_data["enforce_uniform_font"] = font.get("uniform")

    # ---------------------------
    # SPACING RULES
    # ---------------------------
    spacing = parsed.get("spacing_rules", {})

    form_data["main_line_spacing"] = spacing.get("main")
    form_data["reference_spacing"] = spacing.get("reference")
    form_data["certificate_spacing"] = spacing.get("certificate")
    form_data["acknowledgement_spacing"] = spacing.get("acknowledgement")

    # ---------------------------
    # SECTIONS
    # ---------------------------
    sections = parsed.get("sections", [])
    form_data["required_sections"] = ", ".join(sections)

    # ---------------------------
    # CHAPTERS
    # ---------------------------
    chapters = parsed.get("chapters", [])
    form_data["required_chapters"] = ", ".join(chapters)

    # ---------------------------
    # NUMBERING
    # ---------------------------
    numbering = parsed.get("numbering", {})

    form_data["preliminary_numbering"] = numbering.get("preliminary")
    form_data["main_numbering"] = numbering.get("main")
    form_data["page_number_position"] = numbering.get("position")

    # ---------------------------
    # REFERENCES
    # ---------------------------
    ref = parsed.get("reference_rules", {})

    form_data["enforce_reference_alphabetical"] = ref.get("alphabetical")
    form_data["enforce_author_year_format"] = ref.get("author_year")

    # ---------------------------
    # FIGURE/TABLE
    # ---------------------------
    fig = parsed.get("figure_table_rules", {})

    form_data["chapter_based_numbering"] = fig.get("chapter_based")
    form_data["appendix_prefix"] = fig.get("appendix_prefix")

    return form_data
