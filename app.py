import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Add contractor mapping dictionary
CONTRACTOR_MAPPING = {
    "Extension": "Engineer Estimate",
    "Extension.1": "Valley Paving, Inc",
    "Extension.2": "Northwest",
    "Extension.3": "Omann Brothers Paving Inc",
    "Extension.4": "GMH Asphalt Corporation",
    "Extension.5": "Asphalt Surface Technologies Corp",
    "Extension.6": "Park Construction Company",
    "Extension.7": "North Valley, Inc",
    "Extension.8": "Bituminous Roadways Inc",
    "Unit Price": "Engineer Estimate",
    "Unit Price.1": "Valley Paving, Inc",
    "Unit Price.2": "Northwest",
    "Unit Price.3": "Omann Brothers Paving Inc",
    "Unit Price.4": "GMH Asphalt Corporation",
    "Unit Price.5": "Asphalt Surface Technologies Corp",
    "Unit Price.6": "Park Construction Company",
    "Unit Price.7": "North Valley, Inc",
    "Unit Price.8": "Bituminous Roadways Inc",
}


def load_bid_data():
    try:
        # First read all lines to find the actual header
        with open("BidWorksheet.csv", "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        # Find the line containing 'Section Title' which marks our header
        header_index = -1
        for i, line in enumerate(lines):
            if "Section Title" in line:
                header_index = i
                break

        if header_index == -1:
            st.error("Could not find 'Section Title' header row in CSV file")
            st.stop()

        # Read the CSV starting from the header row
        df = pd.read_csv(
            "BidWorksheet.csv",
            skiprows=header_index,
            thousands=",",
            encoding="utf-8-sig",
            na_values=["", "NaN", "nan"],
            keep_default_na=True,
        )

        # Clean up the data
        df = df.dropna(how="all")

        # Keep original columns for value extraction
        original_cols = df.columns.tolist()
        
        # Add section identification before converting columns
        df['Section'] = None
        current_section = None
        for idx, row in df.iterrows():
            if isinstance(row['Section Title'], str) and (
                'Mill and Overlay' in row['Section Title'] or 
                'section - required' in row['Section Title']
            ):
                current_section = row['Section Title']
            df.at[idx, 'Section'] = current_section

        # Store original columns for later reference
        df.attrs["original_cols"] = original_cols
        df.attrs["extension_cols"] = [col for col in original_cols if "Extension" in col]
        df.attrs["unit_price_cols"] = [col for col in original_cols if "Unit Price" in col]
        
        return df

    except Exception as e:
        print(f"Error loading data: {str(e)}")
        st.error(f"Error loading bid data: {str(e)}")
        st.stop()


def get_total_bids(df):
    base_bid_row = df[df['Section Title'].str.contains('Base Bid Total:', na=False)]
    if base_bid_row.empty:
        return pd.Series()
    
    totals = {}
    for col in df.attrs.get("extension_cols", []):
        try:
            value_str = base_bid_row[col].iloc[0]
            if pd.notna(value_str) and str(value_str).strip() != '':
                # Convert string value to float, handling currency format
                value = float(str(value_str).replace('$', '').replace(',', ''))
                if value != 0:
                    contractor = CONTRACTOR_MAPPING.get(col, col)
                    totals[contractor] = value
        except Exception as e:
            print(f"Error processing column {col}: {str(e)}")
            continue
    
    return pd.Series(totals)


def get_section_totals(df):
    section_names = [
        "S.3887 2025 Mill and Overlay",
        "Alternate 1 section - required",
        "Alternate 2 section - required"
    ]
    
    totals_by_section = {}
    for section in section_names:
        section_row = df[df['Section Title'].str.strip() == section]
        if not section_row.empty:
            section_totals = {}
            for col in df.attrs.get("extension_cols", []):
                try:
                    value_str = section_row[col].iloc[0]
                    if pd.notna(value_str) and str(value_str).strip() != '':
                        # Convert string value to float, handling currency format
                        value = float(str(value_str).replace('$', '').replace(',', ''))
                        if value != 0:
                            contractor = CONTRACTOR_MAPPING.get(col, col)
                            section_totals[contractor] = value
                except Exception as e:
                    print(f"Error processing {section} column {col}: {str(e)}")
                    continue
            
            if section_totals:
                totals_by_section[section] = pd.Series(section_totals)
    
    return totals_by_section


def get_line_items_by_section(df):
    """Group line items by section with their unit prices."""
    line_items = {}
    
    # Get unique sections
    sections = df['Section'].unique()
    
    for section in sections:
        if pd.isna(section):
            continue
            
        # Get items for this section
        section_df = df[df['Section'] == section]
        
        # Get unique items in this section
        items = {}
        for _, row in section_df.iterrows():
            if pd.isna(row['Item Description']):
                continue
                
            item_name = f"{row['Item Description']} (Line {row['Line Item']})"
            unit_prices = {}
            
            # Get unit prices for each contractor
            for col in df.attrs.get("unit_price_cols", []):
                try:
                    price_str = row[col]
                    if pd.notna(price_str) and str(price_str).strip() != '':
                        # Convert string value to float, handling currency format
                        price = float(str(price_str).replace('$', '').replace(',', ''))
                        if price != 0:
                            contractor = CONTRACTOR_MAPPING.get(col, col)
                            unit_prices[contractor] = price
                except Exception as e:
                    print(f"Error processing price for {item_name}: {str(e)}")
                    continue
            
            if unit_prices:
                items[item_name] = unit_prices
        
        if items:
            line_items[section] = items
    
    return line_items


def main():
    st.title("Bid Analysis Dashboard")

    try:
        df = load_bid_data()
        totals = get_total_bids(df)
        section_totals = get_section_totals(df)

        st.header("Total Bid Amounts")
        fig, ax = plt.subplots(figsize=(12, 6))
        totals.plot(kind="bar", ax=ax)
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Bid Amount ($)")
        st.pyplot(fig)

        st.header("Comprehensive Bid Comparison")
        # Create a DataFrame with all sections and totals
        comparison_data = {}
        contractors = set()
        
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
            row = {
                "Contractor": contractor,
                "S.3887 2025 Mill and Overlay": comparison_data[contractor].get("S.3887 2025 Mill and Overlay", 0),
                "Alternate 1": comparison_data[contractor].get("Alternate 1 section - required", 0),
                "Alternate 2": comparison_data[contractor].get("Alternate 2 section - required", 0)
            }
            # Calculate total
            row["Total"] = sum(value for key, value in row.items() if key != "Contractor")
            rows.append(row)
        
        # Create DataFrame and sort by Total
        comparison_df = pd.DataFrame(rows)
        comparison_df = comparison_df.sort_values("Total")
        
        # Format currency values
        currency_cols = ["S.3887 2025 Mill and Overlay", "Alternate 1", "Alternate 2", "Total"]
        for col in currency_cols:
            comparison_df[col] = comparison_df[col].map(lambda x: f"${x:,.2f}")
        
        # Set contractor as index
        comparison_df.set_index("Contractor", inplace=True)
        
        # Display the comprehensive table
        st.dataframe(comparison_df)

        # st.header("Section Analysis")
        for section, subtotals in section_totals.items():
            # st.subheader(section)
            if not subtotals.empty:
                # Format subtotals with currency and sort
                formatted_subtotals = subtotals.sort_values().map(lambda x: f"${x:,.2f}")
                # Create a dataframe with custom index name
                section_df = pd.DataFrame(formatted_subtotals, columns=["Bid Amount"])
                section_df.index.name = "Contractor"
        #         st.dataframe(section_df)

        st.header("Individual Line Item Analysis")
        
        # Get items grouped by section
        line_items = get_line_items_by_section(df)
        
        # Create section selector
        selected_section = st.selectbox(
            "Select Section:",
            options=list(line_items.keys())
        )
        
        if selected_section:
            # Create item selector for the selected section
            selected_item = st.selectbox(
                "Select Item:",
                options=list(line_items[selected_section].keys())
            )
            
            if selected_item:
                # Get unit prices for selected item
                unit_prices = line_items[selected_section][selected_item]
                
                # Create bar chart
                fig2, ax2 = plt.subplots(figsize=(12, 6))
                
                contractors = list(unit_prices.keys())
                prices = [unit_prices[c] for c in contractors]
                
                plt.bar(contractors, prices)
                plt.xticks(rotation=45, ha='right')
                plt.ylabel('Unit Price ($)')
                plt.title(f'Unit Prices for {selected_item}\nin {selected_section}')
                
                # Add value labels on top of each bar
                for i, price in enumerate(prices):
                    plt.text(i, price, f'${price:,.2f}', 
                            ha='center', va='bottom')
                
                st.pyplot(fig2)
                
                # Show prices in a table format
                price_df = pd.DataFrame({
                    'Contractor': contractors,
                    'Unit Price': [f'${p:,.2f}' for p in prices]
                }).set_index('Contractor')
                
                # st.dataframe(price_df)
                
                # Show item details if available
                item_details = df[
                    (df['Section'] == selected_section) & 
                    (df['Item Description'].str.strip() == selected_item.split(' (Line ')[0].strip())
                ].iloc[0]
                
                # st.subheader("Item Details")
                details = {
                    'Item Code': item_details['Item Code'],
                    'Unit of Measure': item_details['UofM'],
                    'Quantity': item_details['Quantity']
                }
                # st.write(details)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"Error details: {str(e)}")  # Debug print
        import traceback
        print("Stack trace:", traceback.format_exc())  # Debug print


if __name__ == "__main__":
    main()
