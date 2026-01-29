import pandas as pd

def extract_excel_text(file_path: str):
    sheets = pd.read_excel(file_path, sheet_name=None)
    rows_as_text = []

    for sheet_name, df in sheets.items():
        df = df.dropna(how="all")

        for _, row in df.iterrows():
            row_text = ", ".join(
                f"{col}: {row[col]}"
                for col in df.columns
                if pd.notna(row[col])
            )

            if row_text.strip():
                rows_as_text.append({
                    "page": sheet_name,   # use sheet name as page
                    "text": row_text
                })

    return rows_as_text
