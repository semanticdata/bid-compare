import csv
import re

import pandas as pd


def extract_project_info(csv_file):
    """Extract year and project name from CSV file."""
    match = re.search(r"(20\d{2})", csv_file)
    year = match.group(1) if match else csv_file

    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        first_row = next(reader)
        project_name = first_row[0] if first_row else "Unknown Project"
        project_name = re.sub(r"\s*\([^)]*\)", "", project_name).strip()

    return year, project_name


def calculate_total_bids_by_year(data_by_year):
    """Calculate total bids for each contractor by year."""
    total_bids_by_year = {}
    all_contractors = set()

    for year, d in data_by_year.items():
        section_totals = d["section_totals"]
        total_by_contractor = {}
        for section, subtotals in section_totals.items():
            for contractor, val in subtotals.items():
                total_by_contractor[contractor] = (
                    total_by_contractor.get(contractor, 0) + val
                )
        total_bids_by_year[year] = total_by_contractor
        all_contractors.update(total_by_contractor.keys())

    return total_bids_by_year, sorted(all_contractors)


def prepare_section_breakdown(df, section, contractor_map, selected_contractors):
    """Prepare section breakdown data for display."""
    section_df = df[df["Section"] == section]
    if section_df.empty:
        return None

    table_data = []
    for _, row in section_df.iterrows():
        item = row["Item Description"]
        line = row["Line Item"]
        qty = row["Quantity"]
        row_dict = {"Line": line, "Item": item, "Quantity": qty}

        for contractor, cols in contractor_map.items():
            if contractor not in selected_contractors:
                continue
            unit_col = cols.get("unit_price_col")
            ext_col = cols.get("extension_col")

            unit_val = (
                row.iloc[unit_col]
                if unit_col is not None and unit_col < len(row)
                else None
            )
            ext_val = (
                row.iloc[ext_col]
                if ext_col is not None and ext_col < len(row)
                else None
            )

            row_dict[f"{contractor} Unit"] = unit_val
            row_dict[f"{contractor} Ext"] = ext_val

        table_data.append(row_dict)

    return pd.DataFrame(table_data)


def calculate_total_bids(section_totals_df, present_contractors):
    """Calculate total bids for each contractor."""
    return {
        contractor: section_totals_df[contractor].fillna(0).sum()
        for contractor in present_contractors
    }
