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

        # Convert price columns to numeric and rename them properly
        extension_cols = []
        unit_price_cols = []

        for old_col, new_col in CONTRACTOR_MAPPING.items():
            if old_col in df.columns:
                if "Extension" in old_col:
                    extension_cols.append(new_col)
                    # Convert Extension columns to numeric values
                    df[new_col] = pd.to_numeric(
                        df[old_col].astype(str).replace("[$,]", "", regex=True),
                        errors="coerce",
                    ).fillna(0)
                elif "Unit Price" in old_col:
                    unit_price_cols.append(new_col)
                    # Convert Unit Price columns to numeric values
                    df[new_col] = pd.to_numeric(
                        df[old_col].astype(str).replace("[$,]", "", regex=True),
                        errors="coerce",
                    ).fillna(0)

        # Store the column lists for later use
        df.attrs["extension_cols"] = extension_cols
        df.attrs["unit_price_cols"] = unit_price_cols

        # print("DataFrame shape:", df.shape) # Debug output
        # print("Extension columns:", extension_cols) # Debug output
        # print("Unit Price columns:", unit_price_cols) # Debug output
        return df

    except Exception as e:
        print(f"Error loading data: {str(e)}")
        st.error(f"Error loading bid data: {str(e)}")
        st.stop()


def get_total_bids(df):
    totals = {}
    for col in df.attrs.get("extension_cols", []):
        try:
            # Sum only the valid numeric values, excluding zeros
            values = df[col][df[col] > 0]
            if not values.empty:
                total = values.iloc[0]  # Take the first non-zero value (total bid)
                if total > 0:
                    totals[col] = total
        except Exception as e:
            print(f"Error calculating total for {col}: {str(e)}")
            continue
    return pd.Series(totals)


def main():
    st.title("Bid Analysis Dashboard")

    try:
        df = load_bid_data()
        # print("Loaded DataFrame:", df.head())  # Debug output

        totals = get_total_bids(df)

        st.header("Total Bid Amounts")
        fig, ax = plt.subplots(figsize=(12, 6))
        totals.plot(kind="bar", ax=ax)
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Bid Amount ($)")
        st.pyplot(fig)

        st.header("Bid Comparison Table")
        # Format totals with currency and sort
        formatted_totals = totals.sort_values().map(lambda x: f"${x:,.2f}")
        # Create a dataframe with custom index name
        comparison_df = pd.DataFrame(formatted_totals, columns=["Bid Amount"])
        comparison_df.index.name = "Contractor"
        st.dataframe(comparison_df)

        st.header("Individual Line Item Analysis")
        selected_item = st.selectbox(
            "Select Line Item:", df["Item Description"].unique()
        )

        item_df = df[df["Item Description"] == selected_item]
        if not item_df.empty:
            fig2, ax2 = plt.subplots(figsize=(12, 6))
            unit_price_cols = df.attrs.get("unit_price_cols", [])
            prices = []
            names = []
            for contractor in unit_price_cols:
                price = pd.to_numeric(item_df[contractor].iloc[0], errors="coerce")
                if pd.notna(price) and price > 0:  # Only show valid non-zero prices
                    prices.append(price)
                    names.append(contractor)

            plt.bar(names, prices)
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("Unit Price ($)")
            plt.title(f"Unit Prices for {selected_item}")
            st.pyplot(fig2)

    except Exception as e:
        st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
