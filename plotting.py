import matplotlib.pyplot as plt
import numpy as np


def plot_year_over_year_bids(total_bids_by_year, all_contractors, years):
    """Plots year-over-year total bids by contractor."""
    fig, ax = plt.subplots(figsize=(12, 6))
    for contractor in all_contractors:
        yvals = [total_bids_by_year[y].get(contractor, 0) for y in years]
        ax.plot(years, yvals, marker="o", label=contractor)
        for i, v in enumerate(yvals):
            ax.text(years[i], v, f"${v:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("Year")
    ax.set_ylabel("Total Bid ($)")
    ax.set_title("Total Bids by Contractor (Year-over-Year)")
    ax.legend()
    return fig


def plot_section_totals(section_totals_df, present_contractors):
    """Plots section totals by contractor."""
    fig, ax = plt.subplots(figsize=(15, 8))
    bar_width = 0.8 / max(1, len(present_contractors))
    x = np.arange(len(section_totals_df.index))
    cmap = plt.colormaps["tab10"]
    contractor_colors = {
        contractor: cmap(idx % 10) for idx, contractor in enumerate(present_contractors)
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
    return fig, contractor_colors  # Return colors for reuse


def plot_total_bids_bar_chart(total_bids, contractor_colors):
    """Plots a bar chart of total bids by contractor."""
    fig, ax = plt.subplots(figsize=(8, 5))
    contractors_list = list(total_bids.keys())
    totals_list = [total_bids[c] for c in contractors_list]
    total_colors = [contractor_colors.get(c, "skyblue") for c in contractors_list]
    plt.bar(contractors_list, totals_list, color=total_colors, alpha=0.85)
    plt.ylabel("Total Bid ($)")
    plt.title("Calculated Total Bids by Contractor")
    plt.xticks(rotation=45, ha="right")
    for i, v in enumerate(totals_list):
        plt.text(i, v, f"${v:,.0f}", ha="center", va="bottom")
    plt.tight_layout()
    return fig


def plot_unit_prices(unit_prices, selected_display_item, section):
    """Plots unit prices for a selected item in a section."""
    fig, ax = plt.subplots(figsize=(12, 6))
    contractors = list(unit_prices.keys())
    prices = [unit_prices[c] for c in contractors]
    plt.bar(contractors, prices)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Unit Price ($)")
    plt.title(f"Unit Prices for {selected_display_item}\nin {section}")
    for i, price in enumerate(prices):
        plt.text(i, price, f"${price:,.2f}", ha="center", va="bottom")
    return fig
