import pandas as pd
import streamlit as st


def load_bid_data(filename="BidWorksheet.csv"):
    """
    Loads the bid data from the given filename, dynamically detects contractors and sections, validates numeric fields,
    and collects parse errors. Returns (df, contractor_map, section_list, parse_errors).
    contractor_map: dict of contractor name -> dict with 'unit_price_col' and 'extension_col'.
    section_list: list of all unique section titles.
    parse_errors: list of error messages encountered during parsing.
    """
    try:
        with open(filename, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        contractor_row_index = 5
        header_index = 6
        if len(lines) <= header_index:
            st.error(
                f"CSV file '{filename}' does not have enough rows to read contractor/header info (needs at least {header_index + 1}, found {len(lines)}). Please check the file format."
            )
            return (
                None,
                None,
                None,
                [f"File '{filename}' missing required header rows."],
            )
        import csv

        # Use csv.reader to properly parse quoted names with commas
        contractor_row = next(
            csv.reader([lines[contractor_row_index]], skipinitialspace=True)
        )
        header_row = next(csv.reader([lines[header_index]], skipinitialspace=True))
        # Pad contractor_row to match header_row length
        if len(contractor_row) < len(header_row):
            contractor_row += [""] * (len(header_row) - len(contractor_row))
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
                    contractor_map[contractor]["unit_price_col_name"] = header_row[idx]
                    # Only assign quantity_col if idx-1 >= 0
                    if idx - 1 >= 0:
                        contractor_map[contractor]["quantity_col"] = idx - 1
                        contractor_map[contractor]["quantity_col_name"] = header_row[
                            idx - 1
                        ]
                    # Only assign extension_col if idx+1 < len(header_row):
                    if idx + 1 < len(header_row):
                        contractor_map[contractor]["extension_col"] = idx + 1
                        contractor_map[contractor]["extension_col_name"] = header_row[
                            idx + 1
                        ]
        # print("[DEBUG] Contractor Map:", contractor_map)
        # Read the CSV as DataFrame
        df = pd.read_csv(
            filename,
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
            for contractor, cols in contractor_map.items():
                # Defensive: use header names if present and check bounds
                # Quantity
                quantity_col_name = cols.get("quantity_col_name")
                if quantity_col_name in df.columns and idx + 1 < len(df):
                    quantity_value = df.iloc[idx + 1][quantity_col_name]
                    if pd.notna(quantity_value) and str(quantity_value).strip() != "":
                        try:
                            float(str(quantity_value).replace("$", "").replace(",", ""))
                        except Exception:
                            parse_errors.append(
                                f"Row {idx + 2}: Contractor '{contractor}' quantity value '{quantity_value}' is not numeric."
                            )
                # Unit Price
                unit_price_col_name = cols.get("unit_price_col_name")
                if unit_price_col_name in df.columns and idx + 1 < len(df):
                    unit_price_value = df.iloc[idx + 1][unit_price_col_name]
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
                # Extension
                extension_col_name = cols.get("extension_col_name")
                if extension_col_name in df.columns and idx + 1 < len(df):
                    extension_value = df.iloc[idx + 1][extension_col_name]
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


def get_comparison_table(section_totals, selected_sections):
    """
    Returns a formatted DataFrame for comprehensive bid comparison.
    """
    comparison_data = {}
    contractors = set()
    all_sections = list(section_totals.keys())
    for section, subtotals in section_totals.items():
        for contractor, amount in subtotals.items():
            if contractor not in comparison_data:
                comparison_data[contractor] = {}
            comparison_data[contractor][section] = amount
            contractors.add(contractor)
    rows = []
    for contractor in sorted(contractors):
        row = {"Contractor": contractor}
        for section in all_sections:
            row[section] = comparison_data[contractor].get(section, 0)
        row["Total"] = sum(row[section] for section in all_sections)
        rows.append(row)
    comparison_df = pd.DataFrame(rows)
    if not comparison_df.empty and "Total" in comparison_df.columns:
        comparison_df = comparison_df.sort_values("Total")
    currency_cols = [col for col in all_sections if col in comparison_df.columns]
    if "Total" in comparison_df.columns:
        currency_cols.append("Total")
    for col in currency_cols:
        comparison_df[col] = comparison_df[col].map(lambda x: f"${x:,.2f}")
    if "Contractor" in comparison_df.columns:
        comparison_df.set_index("Contractor", inplace=True)
    return comparison_df


def get_line_items_by_section(df, contractor_map):
    """Group line items by section with their unit prices.
    Returns two dicts:
      - line_items[section][unique_key] = unit_prices
      - display_map[section][display_name] = unique_key
    """
    line_items = {}
    display_map = {}
    sections = df["Section"].unique()
    for section in sections:
        if pd.isna(section):
            continue
        section_df = df[df["Section"] == section]
        items = {}
        display_names = {}
        # Count occurrences for duplicate display names
        desc_counts = section_df["Item Description"].value_counts()
        for _, row in section_df.iterrows():
            if pd.isna(row["Item Description"]):
                continue
            desc = str(row["Item Description"]).strip()
            line = str(row["Line Item"]).strip()
            # Unique key always includes line number
            unique_key = f"{desc} (Line {line})"
            # If duplicate descriptions, append line number to display name
            if desc_counts.get(desc, 0) > 1:
                display_name = f"{desc} [Line {line}]"
            else:
                display_name = desc
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
                items[unique_key] = unit_prices
                display_names[display_name] = unique_key
        if items:
            line_items[section] = items
            display_map[section] = display_names
    return line_items, display_map
