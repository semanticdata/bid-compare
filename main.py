import pandas as pd
import streamlit as st

from data_processing import (
    calculate_total_bids,
    calculate_total_bids_by_year,
    extract_project_info,
    prepare_section_breakdown,
)
from logic import (
    get_comparison_table,
    get_line_items_by_section,
    get_section_totals,
    load_bid_data,
)
from plotting import (
    plot_section_totals,
    plot_total_bids_bar_chart,
    plot_unit_prices,
    plot_year_over_year_bids,
)


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
            year, project_name = extract_project_info(csv_file)
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
            total_bids_by_year_data, all_contractors_list = (
                calculate_total_bids_by_year(data_by_year)
            )
            years_list = sorted(total_bids_by_year_data.keys())
            fig = plot_year_over_year_bids(
                total_bids_by_year_data, all_contractors_list, years_list
            )
            st.pyplot(fig)
            st.markdown("---")
        # Existing single-file analysis continues below
        # st.header("Section Totals Comparison by Contractor")

        # Prepare data for section totals chart
        _section_totals = data_by_year[latest_year]["section_totals"]
        section_totals_df = pd.DataFrame(
            _section_totals
        ).T  # .T might be needed depending on structure

        # Filter contractors that exist in the DataFrame
        available_contractors = [
            c for c in selected_contractors if c in section_totals_df.columns
        ]

        if not section_totals_df.empty and available_contractors:
            section_totals_df = section_totals_df.loc[
                section_totals_df.index.isin(selected_sections), available_contractors
            ]
        else:
            section_totals_df = pd.DataFrame(
                index=selected_sections, columns=available_contractors
            )

        present_contractors = [
            c
            for c in selected_contractors
            if c in section_totals_df.columns
            and not section_totals_df[c].isnull().all()
        ]
        missing_contractors = [
            c for c in selected_contractors if c not in present_contractors
        ]
        section_totals_df = section_totals_df[
            present_contractors
        ]  # Keep only present contractors
        if missing_contractors:
            st.warning(
                f"No data for these contractor(s): {', '.join(missing_contractors)}"
            )
        if present_contractors and not section_totals_df.empty:
            fig, contractor_colors = plot_section_totals(
                section_totals_df, present_contractors
            )
            st.pyplot(fig)

            # --- TOTAL BIDS BAR CHART ---
            # st.header("Calculated Total Bids by Contractor")
            total_bids_calculated = calculate_total_bids(
                section_totals_df, present_contractors
            )
            fig_total = plot_total_bids_bar_chart(
                total_bids_calculated, contractor_colors
            )
            st.pyplot(fig_total)
        else:
            st.info("No data for selected filters.")

        st.header("Comprehensive Bid Comparison")
        comparison_df = get_comparison_table(
            section_totals, selected_sections
        )  # section_totals here is for the latest_year
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
                unit_prices_data = line_items[section][selected_item_key]
                # Filter unit_prices_data for selected_contractors
                unit_prices_filtered = {
                    c: p
                    for c, p in unit_prices_data.items()
                    if c in selected_contractors
                }
                if unit_prices_filtered:
                    fig_unit_price = plot_unit_prices(
                        unit_prices_filtered, selected_display_item, section
                    )
                    st.pyplot(fig_unit_price)
                else:
                    st.info(
                        f"No unit price data for selected contractors in {selected_display_item} for section {section}."
                    )
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
                section_breakdown_df = prepare_section_breakdown(
                    df, section, contractor_map, selected_contractors
                )
                if section_breakdown_df is not None:
                    st.dataframe(section_breakdown_df)
                else:
                    st.write("No items in this section or for the selected contractor.")
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
