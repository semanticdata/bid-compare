import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from logic import load_bid_data, get_section_totals, get_line_items_by_section


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
        # Get project name from first row, first column of BidWorksheet.csv
        import csv

        with open("BidWorksheet.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            first_row = next(reader)
            project_name = first_row[0] if first_row else "Unknown Project"
            import re

            project_name = re.sub(r"\s*\([^)]*\)", "", project_name).strip()
        df, contractor_map, section_list, parse_errors = load_bid_data()
        section_totals = get_section_totals(df, contractor_map, section_list)

        if parse_errors:
            st.warning("Some data issues were detected:")
            for err in parse_errors:
                st.text(err)

        # --- SIDEBAR PROJECT NAME ---
        st.sidebar.header(f"{project_name}")
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

        # Get all line items for item filter
        line_items_all = get_line_items_by_section(df, contractor_map)
        all_items = sorted(
            {item for sec in selected_sections for item in line_items_all.get(sec, {})}
        )
        selected_item = st.sidebar.selectbox(
            "Line Item (for Unit Price Chart)", [None] + all_items
        )

        # --- MAIN LAYOUT ---
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

        # --- UNIT PRICE BAR CHART FOR SELECTED ITEM ---
        if selected_item:
            from logic import prepare_unit_price_chart_data

            st.header(f"Unit Price Comparison for: {selected_item}")
            unit_price_data, unit_df, contractors, prices = (
                prepare_unit_price_chart_data(
                    df,
                    contractor_map,
                    selected_sections,
                    selected_item,
                    selected_contractors,
                )
            )
            if unit_price_data and unit_df is not None:
                fig2, ax2 = plt.subplots(figsize=(10, 5))
                plt.bar(contractors, prices)
                plt.xticks(rotation=45, ha="right")
                plt.ylabel("Unit Price ($)")
                plt.title(f"Unit Prices for {selected_item}")
                for i, price in enumerate(prices):
                    plt.text(i, price, f"${price:,.2f}", ha="center", va="bottom")
                st.pyplot(fig2)
            else:
                st.info("No unit price data for selected item and filters.")

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

        # Get items grouped by section
        line_items = get_line_items_by_section(df, contractor_map)

        # Create section selector
        selected_section = st.selectbox(
            "Select Section:", options=list(line_items.keys())
        )

        if selected_section:
            # Create item selector for the selected section
            selected_item = st.selectbox(
                "Select Item:", options=list(line_items[selected_section].keys())
            )

            if selected_item:
                # Get unit prices for selected item
                unit_prices = line_items[selected_section][selected_item]

                # Create bar chart
                fig2, ax2 = plt.subplots(figsize=(12, 6))

                contractors = list(unit_prices.keys())
                prices = [unit_prices[c] for c in contractors]

                plt.bar(contractors, prices)
                plt.xticks(rotation=45, ha="right")
                plt.ylabel("Unit Price ($)")
                plt.title(f"Unit Prices for {selected_item}\nin {selected_section}")

                # Add value labels on top of each bar
                for i, price in enumerate(prices):
                    plt.text(i, price, f"${price:,.2f}", ha="center", va="bottom")

                st.pyplot(fig2)

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
