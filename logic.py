import pandas as pd
import streamlit as st


def load_bid_data():
    """
    Loads the bid data, dynamically detects contractors and sections, validates numeric fields,
    and collects parse errors. Returns (df, contractor_map, section_list, parse_errors).
    contractor_map: dict of contractor name -> dict with 'unit_price_col' and 'extension_col'.
    section_list: list of all unique section titles.
    parse_errors: list of error messages encountered during parsing.
    """
    try:
        with open("BidWorksheet.csv", "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        # Always use row 6 (index 5) for contractor names
        contractor_row_index = 5
        header_index = 6
        if len(lines) <= header_index:
            st.error("CSV file is missing required header rows.")
            st.stop()
        import csv

        # Use csv.reader to properly parse quoted names with commas
        contractor_row = next(
            csv.reader([lines[contractor_row_index]], skipinitialspace=True)
        )
        header_row = next(csv.reader([lines[header_index]], skipinitialspace=True))
        # print("[DEBUG] header_row:", header_row)
        # print("[DEBUG] contractor_row:", contractor_row)
        # Map each contractor to their Unit Price and Extension columns
        contractor_map = {}
        for idx, col_name in enumerate(header_row):
            if col_name == "Unit Price":
                contractor = contractor_row[idx].strip('" ')
                if contractor:
                    if contractor not in contractor_map:
                        contractor_map[contractor] = {}
                    contractor_map[contractor]["unit_price_col"] = idx
                    # Only assign quantity_col if idx-1 >= 0
                    if idx - 1 >= 0:
                        contractor_map[contractor]["quantity_col"] = idx - 1
                    # Only assign extension_col if idx+1 < len(header_row)
                    if idx + 1 < len(header_row):
                        contractor_map[contractor]["extension_col"] = idx + 1
        # print("[DEBUG] Contractor Map:", contractor_map)
        # Read the CSV as DataFrame
        df = pd.read_csv(
            "BidWorksheet.csv",
            skiprows=header_index,
            thousands=",",
            encoding="utf-8-sig",
            na_values=["", "NaN", "nan"],
            keep_default_na=True,
        )
        df = df.dropna(how="all")
        # print("[DEBUG] First 5 rows of DataFrame:\n", df.head())
        # Identify all unique section titles, EXCLUDING 'Base Bid Total' sections
        section_list = [
            str(s)
            for s in df["Section Title"].dropna().unique()
            if str(s).strip() and "Base Bid Total" not in str(s)
        ]
        # Add section column to each row (forward fill)
        df["Section"] = df["Section Title"].where(df["Section Title"].notna()).ffill()
        # Validate numeric columns and collect errors
        parse_errors = []
        for idx, row in df.iterrows():
            # Validate Quantity, Unit Price, and Extension for each contractor using new mapping
            for contractor, cols in contractor_map.items():
                # Quantity: one row down, one column to the left
                quantity_col = cols.get("quantity_col")
                if quantity_col is None or idx + 1 >= len(df):
                    # print(f"[DEBUG] Skipping contractor '{contractor}' at row {idx+1}: quantity_col index invalid ({quantity_col}) or row out of bounds.")
                    continue
                else:
                    quantity_value = df.iloc[idx + 1, quantity_col]
                    if pd.notna(quantity_value) and str(quantity_value).strip() != "":
                        try:
                            float(str(quantity_value).replace("$", "").replace(",", ""))
                        except Exception:
                            parse_errors.append(
                                f"Row {idx + 2}: Contractor '{contractor}' quantity value '{quantity_value}' is not numeric."
                            )
                # Unit Price: one row down, same column
                unit_price_col = cols.get("unit_price_col")
                if unit_price_col is None or idx + 1 >= len(df):
                    # print(f"[DEBUG] Skipping contractor '{contractor}' at row {idx+1}: unit_price_col index invalid ({unit_price_col}) or row out of bounds.")
                    continue
                else:
                    unit_price_value = df.iloc[idx + 1, unit_price_col]
                    if (
                        pd.notna(unit_price_value)
                        and str(unit_price_value).strip() != ""
                    ):
                        try:
                            float(
                                str(unit_price_value).replace("$", "").replace(",", "")
                            )
                        except Exception:
                            parse_errors.append(
                                f"Row {idx + 2}: Contractor '{contractor}' unit price value '{unit_price_value}' is not numeric."
                            )
                # Extension: one row down, one column to the right
                extension_col = cols.get("extension_col")
                if extension_col is None or idx + 1 >= len(df):
                    print(
                        f"[DEBUG] Skipping contractor '{contractor}' at row {idx + 1}: extension_col index invalid ({extension_col}) or row out of bounds."
                    )
                else:
                    extension_value = df.iloc[idx + 1, extension_col]
                    if pd.notna(extension_value) and str(extension_value).strip() != "":
                        try:
                            float(
                                str(extension_value).replace("$", "").replace(",", "")
                            )
                        except Exception:
                            parse_errors.append(
                                f"Row {idx + 2}: Contractor '{contractor}' extension value '{extension_value}' is not numeric."
                            )
        return df, contractor_map, section_list, parse_errors
    except Exception as e:
        st.error(f"Error loading bid data: {e}")
        st.stop()


def get_total_bids(df, contractor_map):
    base_bid_row = df[
        df["Section Title"].astype(str).str.contains("Base Bid Total:", na=False)
    ]
    if base_bid_row.empty:
        return pd.Series()
    totals = {}
    row = base_bid_row.iloc[0]
    for contractor, cols in contractor_map.items():
        ext_col_idx = cols.get("extension_col")
        if ext_col_idx is not None and ext_col_idx < len(row):
            value_str = row.iloc[ext_col_idx]
            if pd.notna(value_str) and str(value_str).strip() != "":
                try:
                    value = float(str(value_str).replace("$", "").replace(",", ""))
                    if value != 0:
                        totals[contractor] = value
                except Exception:
                    continue
    return pd.Series(totals)


def get_section_totals(df, contractor_map, section_list):
    totals_by_section = {}
    for section in section_list:
        section_row = df[df["Section Title"].astype(str).str.strip() == section]
        if not section_row.empty:
            section_totals = {}
            row = section_row.iloc[0]
            for contractor, cols in contractor_map.items():
                ext_col_idx = cols.get("extension_col")
                if ext_col_idx is not None and ext_col_idx < len(row):
                    value_str = row.iloc[ext_col_idx]
                    if pd.notna(value_str) and str(value_str).strip() != "":
                        try:
                            value = float(
                                str(value_str).replace("$", "").replace(",", "")
                            )
                            if value != 0:
                                section_totals[contractor] = value
                        except Exception:
                            continue
            if section_totals:
                totals_by_section[section] = pd.Series(section_totals)
    return totals_by_section


def get_section_totals_df(df, contractor_map, section_list, selected_contractors=None):
    """
    Returns a DataFrame with sections as rows, contractors as columns, and values as bid totals.
    If selected_contractors is provided, only those contractors are included.
    """
    data = {}
    for section in section_list:
        section_row = df[df["Section Title"].astype(str).str.strip() == section]
        if not section_row.empty:
            row = section_row.iloc[0]
            row_data = {}
            for contractor, cols in contractor_map.items():
                if selected_contractors and contractor not in selected_contractors:
                    continue
                ext_col_idx = cols.get("extension_col")
                if ext_col_idx is not None and ext_col_idx < len(row):
                    value_str = row.iloc[ext_col_idx]
                    if pd.notna(value_str) and str(value_str).strip() != "":
                        try:
                            value = float(
                                str(value_str).replace("$", "").replace(",", "")
                            )
                            row_data[contractor] = value
                        except Exception:
                            row_data[contractor] = None
            data[section] = row_data
    return pd.DataFrame(data).T  # sections as rows, contractors as columns


def get_line_items_by_section(df, contractor_map):
    """Group line items by section with their unit prices."""
    line_items = {}
    sections = df["Section"].unique()
    for section in sections:
        if pd.isna(section):
            continue
        section_df = df[df["Section"] == section]
        items = {}
        for _, row in section_df.iterrows():
            if pd.isna(row["Item Description"]):
                continue
            item_name = f"{row['Item Description']} (Line {row['Line Item']})"
            unit_prices = {}
            for contractor, cols in contractor_map.items():
                unit_col_idx = cols.get("unit_price_col")
                if unit_col_idx is not None and unit_col_idx < len(row):
                    price_str = row.iloc[unit_col_idx]
                    if pd.notna(price_str) and str(price_str).strip() != "":
                        try:
                            price = float(
                                str(price_str).replace("$", "").replace(",", "")
                            )
                            if price != 0:
                                unit_prices[contractor] = price
                        except Exception:
                            continue
            if unit_prices:
                items[item_name] = unit_prices
        if items:
            line_items[section] = items
    return line_items
