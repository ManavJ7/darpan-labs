"""
Export LLM log JSONL to a clean PDF document.

Usage:
    python scripts/export_llm_log_pdf.py [--input <path>] [--output <path>]
"""
import argparse
import json
import textwrap
from pathlib import Path

from fpdf import FPDF


def safe_text(text: str) -> str:
    """Replace problematic Unicode characters with ASCII equivalents."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
        "\u20b9": "Rs.",  # Indian rupee sign
        "\u2248": "~",    # approximately
        "\u2265": ">=",   # greater than or equal
        "\u2264": "<=",   # less than or equal
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class LogPDF(FPDF):
    """Custom PDF with header/footer."""

    def __init__(self, title: str = "LLM Simulation Log"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, safe_text(self.doc_title), align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def add_section_title(pdf: LogPDF, text: str):
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(25, 60, 120)
    pdf.cell(0, 10, safe_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(25, 60, 120)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)


def add_meta_line(pdf: LogPDF, label: str, value: str):
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(30, 5, safe_text(label + ":"))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 5, safe_text(value), new_x="LMARGIN", new_y="NEXT")


def add_block(pdf: LogPDF, heading: str, body: str, heading_color=(180, 60, 30), max_chars=12000):
    """Add a labeled text block (Prompt or Response)."""
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*heading_color)
    pdf.cell(0, 6, safe_text(heading), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(30, 30, 30)

    # Truncate extremely long blocks to keep PDF reasonable
    if len(body) > max_chars:
        body = body[:max_chars] + f"\n\n... [truncated — {len(body):,} chars total]"

    # Wrap long lines and write
    for line in body.split("\n"):
        wrapped = textwrap.wrap(line, width=115) or [""]
        for wl in wrapped:
            pdf.cell(0, 3.2, safe_text(wl), new_x="LMARGIN", new_y="NEXT")


def format_response_pretty(raw: str) -> str:
    """Try to pretty-print JSON responses, fall back to raw text."""
    try:
        obj = json.loads(raw)
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return raw


def build_pdf(input_path: Path, output_path: Path):
    """Read JSONL log and produce a formatted PDF."""
    entries = []
    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    # Separate by type
    batches = {}
    kg_entry = None
    for e in entries:
        bid = e["batch_id"]
        ct = e["call_type"]
        if ct == "kg_extraction":
            kg_entry = e
        else:
            batches.setdefault(bid, {})[ct] = e

    pdf = LogPDF(title="P01_T001 Survey Simulation — LLM Log")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title page
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(25, 60, 120)
    pdf.ln(30)
    pdf.cell(0, 12, "Digital Twin Survey Simulation", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "LLM Prompts & Responses", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)

    # Summary info
    model = entries[0].get("model", "unknown") if entries else "unknown"
    twin_id = entries[0].get("twin_id", "unknown") if entries else "unknown"
    timestamp = entries[0].get("timestamp", "") if entries else ""
    n_synthesis = sum(1 for e in entries if e["call_type"] == "batch_synthesis")
    total_elapsed = sum(e.get("elapsed_s", 0) for e in entries)

    lines = [
        f"Twin: {twin_id}",
        f"Model: {model}",
        f"Timestamp: {timestamp[:19]}",
        f"Synthesis batches: {n_synthesis}",
        f"Total LLM calls: {len(entries)}",
        f"Total LLM time: {total_elapsed:.0f}s",
    ]
    for l in lines:
        pdf.cell(0, 7, safe_text(l), align="C", new_x="LMARGIN", new_y="NEXT")

    # Process each batch
    for bid in sorted(batches.keys()):
        batch = batches[bid]
        pdf.add_page()

        add_section_title(pdf, f"Batch {bid}")

        # Domain classification (short)
        if "domain_classification" in batch:
            dc = batch["domain_classification"]
            add_meta_line(pdf, "Domains", dc["response"])
            add_meta_line(pdf, "Time", f"{dc['elapsed_s']:.1f}s")
            pdf.ln(2)

        # Synthesis (the main prompt + response)
        if "batch_synthesis" in batch:
            syn = batch["batch_synthesis"]
            add_meta_line(pdf, "Time", f"{syn['elapsed_s']:.1f}s")
            add_meta_line(pdf, "Prompt size", f"{len(syn['prompt']):,} chars")
            add_meta_line(pdf, "Response size", f"{len(syn['response']):,} chars")

            add_block(pdf, "PROMPT", syn["prompt"], heading_color=(25, 100, 60))
            add_block(
                pdf,
                "RESPONSE",
                format_response_pretty(syn["response"]),
                heading_color=(180, 60, 30),
            )

    # KG extraction at the end
    if kg_entry:
        pdf.add_page()
        add_section_title(pdf, "Post-Simulation: KG Trait Extraction")
        add_meta_line(pdf, "Time", f"{kg_entry['elapsed_s']:.1f}s")
        add_meta_line(pdf, "Response size", f"{len(kg_entry['response']):,} chars")

        add_block(pdf, "PROMPT", kg_entry["prompt"], heading_color=(25, 100, 60))
        add_block(
            pdf,
            "RESPONSE (Extracted Traits)",
            format_response_pretty(kg_entry["response"]),
            heading_color=(180, 60, 30),
            max_chars=18000,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"PDF saved to: {output_path}")
    print(f"  Pages: {pdf.page_no()}")
    print(f"  Size: {output_path.stat().st_size / 1024:.0f} KB")


def main():
    parser = argparse.ArgumentParser(description="Export LLM log to PDF")
    parser.add_argument(
        "--input",
        default="data/output/step5_simulation/llm_log_P01_T001_20260306_003250.jsonl",
        help="Path to JSONL log file",
    )
    parser.add_argument(
        "--output",
        default="data/output/step5_simulation/P01_T001_simulation_llm_log.pdf",
        help="Output PDF path",
    )
    args = parser.parse_args()
    build_pdf(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
