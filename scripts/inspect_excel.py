import pandas as pd
import sys

def inspect_excel(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        sheet1_name = xls.sheet_names[0]
        sheet2_name = xls.sheet_names[1]

        df1 = pd.read_excel(xls, sheet_name=sheet1_name)
        df2 = pd.read_excel(xls, sheet_name=sheet2_name)

        print("--- Sheet 1: Common Foods ---")
        print(f"Columns: {df1.columns.tolist()}")
        print("Head:")
        print(df1.head().to_string())

        print("\n--- Sheet 2: PMOS Foods ---")
        print(f"Columns: {df2.columns.tolist()}")
        print("Head:")
        print(df2.head().to_string())

    except Exception as e:
        print(f"Error inspecting Excel file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_excel(sys.argv[1])
    else:
        print("Usage: python inspect_excel.py <file_path>", file=sys.stderr)
        sys.exit(1)
