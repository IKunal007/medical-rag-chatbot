from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Image,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from PIL import Image as PILImage

def assemble_pdf(report_state, output_path):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportBody",
        fontName="Times-Roman",
        fontSize=11.5,
        leading=16,      
        spaceAfter=10,
        alignment=TA_JUSTIFY
    ))

    styles.add(ParagraphStyle(
        name="ReportHeading",
        fontName="Times-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=14,
        spaceBefore=6
    ))
    doc = SimpleDocTemplate(
    str(output_path),
    rightMargin=48,
    leftMargin=48,
    topMargin=56,
    bottomMargin=56
    )

    elements = []

    for idx, (section, data) in enumerate(report_state.items()):

        if idx > 0:
            elements.append(PageBreak())
        # -----------------------------
        # Section header
        # -----------------------------
        elements.append(Paragraph(section, styles["ReportHeading"]))
        elements.append(Spacer(1, 12))

        # -----------------------------
        # Text sections
        # -----------------------------
        if data["type"] == "text":
            if data["content"].strip():
                elements.append(Paragraph(data["content"], styles["ReportBody"]))
        # -----------------------------
        # Images
        # -----------------------------
        elif data["type"] == "images":
            for img in data["content"]:
                elements.append(scaled_image(str(img)))
                elements.append(Spacer(1, 12))
        # -----------------------------
        # Tables (FIXED)
        # -----------------------------
        elif data["type"] == "tables":
            for table in data["content"]:
                rows = table.get("rows")

                # 🚫 Skip empty or broken tables
                if not rows or len(rows) < 2:
                    continue
                
                # 1️⃣ Split table by logical row headers
                row_tables = split_table_by_row_headers(rows)

                for row_table in row_tables:
                    num_cols = len(row_table[0])

                    # 2️⃣ Split wide tables by columns
                    if num_cols <= 4:
                        column_tables = [row_table]
                    else:
                        column_tables = split_table_by_columns(
                            row_table,
                            max_data_cols=3
                        )

                    for split_rows in column_tables:
                        num_cols = len(split_rows[0])
                        col_widths = [doc.width / num_cols] * num_cols

                        tbl = Table(
                            split_rows,
                            colWidths=col_widths,
                            repeatRows=1
                        )

                        tbl.setStyle(TableStyle([
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]))

                        elements.append(tbl)
                        elements.append(Spacer(1, 16))


    print("Saving PDF for session:")
    print("Final path:", output_path)

    doc.build(elements)


def scaled_image(path, max_width=400, max_height=500):
    img = PILImage.open(path)
    w, h = img.size

    scale = min(max_width / w, max_height / h)
    return Image(
        path,
        width=w * scale,
        height=h * scale,
        hAlign="CENTER",
    )

def split_table_by_columns(rows, max_data_cols=3):
    header = rows[0]
    body = rows[1:]

    fixed_cols = 1  # first column is row label
    data_cols = len(header) - fixed_cols

    tables = []
    start = 0

    while start < data_cols:
        end = min(start + max_data_cols, data_cols)

        cols = [0] + list(range(fixed_cols + start, fixed_cols + end))

        # SAFE slicing
        split_header = [header[i] for i in cols if i < len(header)]
        split_rows = [split_header]

        for row in body:
            split_row = [row[i] for i in cols if i < len(row)]
            split_rows.append(split_row)

        tables.append(split_rows)
        start = end

    return tables

def split_table_by_row_headers(rows):
    """
    Splits a table into sub-tables when a row looks like a section header.
    """
    header = rows[0]
    data_rows = rows[1:]

    tables = []
    current_rows = [header]

    for row in data_rows:
        first_cell = str(row[0]).lower()

        # Heuristic: section titles inside tables
        if (
            "summary statistics" in first_cell
            or "variables at" in first_cell
        ):
            if len(current_rows) > 1:
                tables.append(current_rows)
            current_rows = [header]  # reset table with same header
            continue

        current_rows.append(row)

    if len(current_rows) > 1:
        tables.append(current_rows)

    return tables
