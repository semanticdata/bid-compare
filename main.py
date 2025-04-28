import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from logic import load_bid_data, get_section_totals, get_line_items_by_section



def main():
    st.set_page_config(page_title="Bid Compare", page_icon=None, layout="centered", initial_sidebar_state="auto", menu_items=None)
    st.title("Bid Analysis Dashboard")

    try:
        df, contractor_map, section_list, parse_errors = load_bid_data()
        section_totals = get_section_totals(df, contractor_map, section_list)

        if parse_errors:
            st.warning('Some data issues were detected:')
            for err in parse_errors:
                st.text(err)

        # --- SIDEBAR FILTERS ---
        st.sidebar.header("Filters")
        contractor_options = list(contractor_map.keys())
        section_options = section_list
        selected_contractors = st.sidebar.multiselect("Contractors", contractor_options, default=contractor_options)
        selected_sections = st.sidebar.multiselect("Sections", section_options, default=section_options)

        # Get all line items for item filter
        line_items_all = get_line_items_by_section(df, contractor_map)
        all_items = sorted({item for sec in selected_sections for item in line_items_all.get(sec, {})})
        selected_item = st.sidebar.selectbox("Line Item (for Unit Price Chart)", [None] + all_items)

        # --- MAIN LAYOUT ---
        st.header("Section Totals Comparison by Contractor")
        from logic import get_section_totals_df
        section_totals_df = get_section_totals_df(df, contractor_map, section_list, selected_contractors)
        section_totals_df = section_totals_df.loc[section_totals_df.index.isin(selected_sections)]
        # Only use contractors present in the DataFrame columns
        present_contractors = [c for c in selected_contractors if c in section_totals_df.columns]
        missing_contractors = [c for c in selected_contractors if c not in section_totals_df.columns]
        if missing_contractors:
            st.warning(f"No data for these contractor(s): {', '.join(missing_contractors)}")
        if present_contractors and not section_totals_df.empty:
            fig, ax = plt.subplots(figsize=(15, 8))
            bar_width = 0.8 / max(1, len(present_contractors))
            x = np.arange(len(section_totals_df.index))
            for idx, contractor in enumerate(present_contractors):
                values = section_totals_df[contractor].fillna(0).values
                positions = x + idx * bar_width
                plt.bar(positions, values, bar_width, label=contractor, alpha=0.8)
                for i, v in enumerate(values):
                    plt.text(positions[i], v, f"${v:,.0f}", ha="center", va="bottom", rotation=45, fontsize=8)
            plt.xlabel("Sections")
            plt.ylabel("Bid Amount ($)")
            plt.title("Section Totals by Contractor")
            plt.xticks(x + bar_width * (len(present_contractors)-1)/2, section_totals_df.index, rotation=45, ha="right")
            plt.legend()
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No data for selected filters.")

        # --- SECTION BREAKDOWN TABLE ---
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
                    unit_col = cols.get('unit_price_col')
                    ext_col = cols.get('extension_col')
                    unit_val = row.iloc[unit_col] if unit_col is not None and unit_col < len(row) else None
                    ext_val = row.iloc[ext_col] if ext_col is not None and ext_col < len(row) else None
                    row_dict[f"{contractor} Unit"] = unit_val
                    row_dict[f"{contractor} Ext"] = ext_val
                table_data.append(row_dict)
            st.dataframe(pd.DataFrame(table_data))

        # --- UNIT PRICE BAR CHART FOR SELECTED ITEM ---
        if selected_item:
            st.header(f"Unit Price Comparison for: {selected_item}")
            unit_price_data = []
            for section in selected_sections:
                items = line_items_all.get(section, {})
                if selected_item in items:
                    for contractor, price in items[selected_item].items():
                        if contractor in selected_contractors:
                            unit_price_data.append({
                                "Contractor": contractor,
                                "Section": section,
                                "Unit Price": price
                            })
            if unit_price_data:
                unit_df = pd.DataFrame(unit_price_data)
                fig2, ax2 = plt.subplots(figsize=(10, 5))
                contractors = unit_df["Contractor"].unique()
                prices = [unit_df[unit_df["Contractor"] == c]["Unit Price"].iloc[0] if not unit_df[unit_df["Contractor"] == c].empty else 0 for c in contractors]
                plt.bar(contractors, prices)
                plt.xticks(rotation=45, ha="right")
                plt.ylabel("Unit Price ($)")
                plt.title(f"Unit Prices for {selected_item}")
                for i, price in enumerate(prices):
                    plt.text(i, price, f"${price:,.2f}", ha="center", va="bottom")
                st.pyplot(fig2)
            else:
                st.info("No unit price data for selected item and filters.")

        # --- CONTRACTOR SUMMARY TABLE ---
        st.header("Contractor Summary Table")
        summary_data = []
        for contractor in selected_contractors:
            contractor_sections = [totals.get(contractor, 0) for section, totals in section_totals.items() if section in selected_sections]
            if contractor_sections:
                summary_data.append({
                    "Contractor": contractor,
                    "Total": sum(contractor_sections),
                    "Min": min(contractor_sections),
                    "Max": max(contractor_sections),
                    "Average": sum(contractor_sections)/len(contractor_sections)
                })
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df["Total"] = summary_df["Total"].map(lambda x: f"${x:,.2f}")
            summary_df["Min"] = summary_df["Min"].map(lambda x: f"${x:,.2f}")
            summary_df["Max"] = summary_df["Max"].map(lambda x: f"${x:,.2f}")
            summary_df["Average"] = summary_df["Average"].map(lambda x: f"${x:,.2f}")
            st.dataframe(summary_df.set_index("Contractor"))
        else:
            st.info("No summary data for selected filters.")


        st.header("Comprehensive Bid Comparison")
        # Create a DataFrame with all sections and totals
        comparison_data = {}
        contractors = set()

        # Use the dynamic section list
        all_sections = list(section_totals.keys())

        # Collect all contractor names and their bids from each section
        for section, subtotals in section_totals.items():
            for contractor, amount in subtotals.items():
                if contractor not in comparison_data:
                    comparison_data[contractor] = {}
                comparison_data[contractor][section] = amount
                contractors.add(contractor)

        # Calculate sum of sections for each contractor
        rows = []
        for contractor in sorted(contractors):
            row = {"Contractor": contractor}
            for section in all_sections:
                row[section] = comparison_data[contractor].get(section, 0)
            # Calculate total
            row["Total"] = sum(row[section] for section in all_sections)
            rows.append(row)

        # Create DataFrame and sort by Total if present
        comparison_df = pd.DataFrame(rows)
        if not comparison_df.empty and "Total" in comparison_df.columns:
            comparison_df = comparison_df.sort_values("Total")

        # Format currency values
        currency_cols = [col for col in all_sections if col in comparison_df.columns]
        if "Total" in comparison_df.columns:
            currency_cols.append("Total")
        for col in currency_cols:
            comparison_df[col] = comparison_df[col].map(lambda x: f"${x:,.2f}")

        # Set contractor as index and display only if present
        if "Contractor" in comparison_df.columns:
            comparison_df.set_index("Contractor", inplace=True)
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

                # Show prices in a table format
                # Show item details if available
                # If you want to display details, uncomment below:
                # item_details = df[
                #     (df["Section"] == selected_section)
                #     & (
                #         df["Item Description"].str.strip()
                #         == selected_item.split(" (Line ")[0].strip()
                #     )
                # ].iloc[0]
                # st.subheader("Item Details")
                # st.write({
                #     "Item Code": item_details["Item Code"],
                #     "Unit of Measure": item_details["UofM"],
                #     "Quantity": item_details["Quantity"],
                # })

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"Error details: {str(e)}")  # Debug print
        import traceback

        print("Stack trace:", traceback.format_exc())  # Debug print


if __name__ == "__main__":
    main()
