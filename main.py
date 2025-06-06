import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from logic import get_line_items_by_section, get_section_totals, load_bid_data


def main():
    st.set_page_config(
        page_title="Bid Compare",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="auto",
        menu_items=None,
    )
    st.title("Bid Analysis Dashboard")

    try:
        import csv
        import os

        # Find all CSV files in the root directory
        csv_files = [f for f in os.listdir(".") if f.lower().endswith(".csv")]
        selected_csvs = st.sidebar.multiselect(
            "Select Bid CSV File(s) for Year-over-Year Comparison",
            csv_files,
            default=sorted(csv_files)[-1:],  # Default to latest file
        )
        data_by_year = {}
        project_names = {}
        parse_errors_all = []
        for csv_file in selected_csvs:
            # Extract year from filename (e.g., 2023_MillandOverlay_BidWorksheet.csv -> 2023)
            match = re.search(r"(20\d{2})", csv_file)
            year = match.group(1) if match else csv_file
            with open(csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                first_row = next(reader)
                project_name = first_row[0] if first_row else "Unknown Project"
                project_name = re.sub(r"\s*\([^)]*\)", "", project_name).strip()
                project_names[year] = project_name
            df, contractor_map, section_list, parse_errors = load_bid_data(csv_file)
            data_by_year[year] = {
                "df": df,
                "contractor_map": contractor_map,
                "section_list": section_list,
                "section_totals": get_section_totals(df, contractor_map, section_list),
            }
            if parse_errors:
                parse_errors_all.extend([f"{csv_file}: {err}" for err in parse_errors])
        # Show errors if any
        if parse_errors_all:
            st.warning("Some data issues were detected:")
            for err in parse_errors_all:
                st.text(err)
        # --- SIDEBAR PROJECT NAME (show all selected) ---
        st.sidebar.header(
            ", ".join([project_names[y] for y in sorted(project_names.keys())])
        )
        # If no file selected, stop
        if not selected_csvs:
            st.info("Please select at least one CSV file.")
            st.stop()
        # Use the latest year for default filters
        latest_year = sorted(data_by_year.keys())[-1]
        df = data_by_year[latest_year]["df"]
        contractor_map = data_by_year[latest_year]["contractor_map"]
        section_list = data_by_year[latest_year]["section_list"]
        section_totals = data_by_year[latest_year]["section_totals"]

        # --- SIDEBAR FILTERS ---
        st.sidebar.header("Filters")
        contractor_options = list(contractor_map.keys())
        section_options = section_list
        selected_contractors = st.sidebar.multiselect(
            "Contractors", contractor_options, default=contractor_options
        )
        selected_sections = st.sidebar.multiselect(
            "Sections", section_options, default=section_options
        )
        # Get all line items for item filter (returns (line_items, display_map))
        line_items_all, display_map_all = get_line_items_by_section(df, contractor_map)
        # Build display-to-unique-key mapping for selected sections
        display_to_key = {}
        for sec in selected_sections:
            if sec in display_map_all:
                display_to_key.update(display_map_all[sec])
        all_display_items = sorted(display_to_key.keys())
        selected_display_item = st.sidebar.selectbox(
            "Line Item (for Unit Price Chart)", [None] + all_display_items
        )
        selected_item_key = (
            display_to_key[selected_display_item] if selected_display_item else None
        )

        # --- MAIN LAYOUT ---
        # --- YEAR-OVER-YEAR ANALYSIS ---
        if len(selected_csvs) > 1:
            st.header("Year-over-Year Total Bids by Contractor")
            # Prepare data
            total_bids_by_year = {}
            all_contractors = set()
            for year, d in data_by_year.items():
                section_totals = d["section_totals"]
                # Sum all section totals for each contractor
                total_by_contractor = {}
                for section, subtotals in section_totals.items():
                    for contractor, val in subtotals.items():
                        total_by_contractor[contractor] = (
                            total_by_contractor.get(contractor, 0) + val
                        )
                total_bids_by_year[year] = total_by_contractor
                all_contractors.update(total_by_contractor.keys())
            all_contractors = sorted(all_contractors)
            years = sorted(total_bids_by_year.keys())
            fig, ax = plt.subplots(figsize=(12, 6))
            for contractor in all_contractors:
                yvals = [total_bids_by_year[y].get(contractor, 0) for y in years]
                ax.plot(years, yvals, marker="o", label=contractor)
                for i, v in enumerate(yvals):
                    ax.text(
                        years[i], v, f"${v:,.0f}", ha="center", va="bottom", fontsize=8
                    )
            ax.set_xlabel("Year")
            ax.set_ylabel("Total Bid ($)")
            ax.set_title("Total Bids by Contractor (Year-over-Year)")
            ax.legend()
            st.pyplot(fig)
            st.markdown("---")
        # Existing single-file analysis continues below
        # st.header("Section Totals Comparison by Contractor")

        from logic import prepare_section_totals_chart_data

        section_totals_df, present_contractors, missing_contractors = (
            prepare_section_totals_chart_data(
                df,
                contractor_map,
                section_list,
                selected_contractors,
                selected_sections,
            )
        )
        if missing_contractors:
            st.warning(
                f"No data for these contractor(s): {', '.join(missing_contractors)}"
            )
        if present_contractors and not section_totals_df.empty:
            fig, ax = plt.subplots(figsize=(15, 8))
            bar_width = 0.8 / max(1, len(present_contractors))
            x = np.arange(len(section_totals_df.index))
            cmap = plt.colormaps["tab10"]
            contractor_colors = {
                contractor: cmap(idx % 10)
                for idx, contractor in enumerate(present_contractors)
            }
            for idx, contractor in enumerate(present_contractors):
                values = section_totals_df[contractor].fillna(0).values
                positions = x + idx * bar_width
                plt.bar(
                    positions,
                    values,
                    bar_width,
                    label=contractor,
                    alpha=0.8,
                    color=contractor_colors[contractor],
                )
                for i, v in enumerate(values):
                    plt.text(
                        positions[i],
                        v,
                        f"${v:,.0f}",
                        ha="center",
                        va="bottom",
                        rotation=45,
                        fontsize=8,
                    )
            plt.xlabel("Sections")
            plt.ylabel("Bid Amount ($)")
            plt.title("Section Totals by Contractor")
            plt.xticks(
                x + bar_width * (len(present_contractors) - 1) / 2,
                section_totals_df.index,
                rotation=45,
                ha="right",
            )
            plt.legend()
            plt.tight_layout()
            st.pyplot(fig)

            # --- TOTAL BIDS BAR CHART ---
            # st.header("Calculated Total Bids by Contractor")
            # Calculate total bid for each present contractor
            total_bids = {}
            for contractor in present_contractors:
                total_bids[contractor] = section_totals_df[contractor].fillna(0).sum()
            fig_total, ax_total = plt.subplots(figsize=(8, 5))
            contractors_list = list(total_bids.keys())
            totals_list = [total_bids[c] for c in contractors_list]
            total_colors = [
                contractor_colors.get(c, "skyblue") for c in contractors_list
            ]
            plt.bar(contractors_list, totals_list, color=total_colors, alpha=0.85)
            plt.ylabel("Total Bid ($)")
            plt.title("Calculated Total Bids by Contractor")
            plt.xticks(rotation=45, ha="right")
            for i, v in enumerate(totals_list):
                plt.text(i, v, f"${v:,.0f}", ha="center", va="bottom")
            plt.tight_layout()
            st.pyplot(fig_total)
        else:
            st.info("No data for selected filters.")

        st.header("Comprehensive Bid Comparison")
        from logic import get_comparison_table

        comparison_df = get_comparison_table(section_totals, selected_sections)
        if not comparison_df.empty:
            st.dataframe(comparison_df)
        else:
            st.info("No contractor data available for the selected filters.")

        # st.header("Section Analysis")
        for section, subtotals in section_totals.items():
            # st.subheader(section)
            if not subtotals.empty:
                # Format subtotals with currency and sort
                formatted_subtotals = subtotals.sort_values().map(
                    lambda x: f"${x:,.2f}"
                )
                # Create a dataframe with custom index name
                section_df = pd.DataFrame(formatted_subtotals, columns=["Bid Amount"])
                section_df.index.name = "Contractor"
        #         st.dataframe(section_df)

        st.header("Individual Line Item Analysis")

        # Use sidebar filters for section and item
        # Only show chart if one section is selected and an item is selected
        if len(selected_sections) == 1 and selected_item_key:
            section = selected_sections[0]
            line_items, _ = get_line_items_by_section(df, contractor_map)
            if section in line_items and selected_item_key in line_items[section]:
                unit_prices = line_items[section][selected_item_key]
                fig2, ax2 = plt.subplots(figsize=(12, 6))
                contractors = list(unit_prices.keys())
                prices = [unit_prices[c] for c in contractors]
                plt.bar(contractors, prices)
                plt.xticks(rotation=45, ha="right")
                plt.ylabel("Unit Price ($)")
                plt.title(f"Unit Prices for {selected_display_item}\nin {section}")
                # Add value labels on top of each bar
                for i, price in enumerate(prices):
                    plt.text(i, price, f"${price:,.2f}", ha="center", va="bottom")
                st.pyplot(fig2)
            else:
                st.info("No unit price data for selected item and section.")
        else:
            st.info(
                "Please select exactly one section and an item in the sidebar to view line item analysis."
            )

        # --- SECTION BREAKDOWN TABLE ---
        if len(selected_contractors) == 1:
            st.header("Section Breakdown Table")
            for section in selected_sections:
                st.subheader(f"Section: {section}")
                section_df = df[df["Section"] == section]
                if section_df.empty:
                    st.write("No items in this section.")
                    continue
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
                st.dataframe(pd.DataFrame(table_data))
        elif len(selected_contractors) > 1:
            st.info(
                "Section Breakdown Table is only available when a single contractor is selected."
            )

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"Error details: {str(e)}")  # Debug print
        import traceback

        print("Stack trace:", traceback.format_exc())  # Debug print


if __name__ == "__main__":
    main()
