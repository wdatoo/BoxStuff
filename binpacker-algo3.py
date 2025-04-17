import streamlit as st
import pandas as pd
import numpy as np
import io

# Function to implement Bin Packing with Optimization and Constraints
def pack_bins_optimized(df: pd.DataFrame, max_bin_weight: int, min_bin_weight: int, max_items_per_bin: int) -> pd.DataFrame:
    # Sort by TruckNumber first, then by GrossWeight descending
    sorted_df = df.sort_values(by=["TruckNumber", "GrossWeight"], ascending=[True, False]).reset_index(drop=True)
    
    bins = []
    bin_weights_gross = []
    bin_weights_nett = []
    bin_items_count = []
    
    truck_bins = {}  # Dictionary to track which bin a truck is assigned to
    
    for index, row in sorted_df.iterrows():
        truck = row["TruckNumber"]
        placed = False

        # Find the best-fit bin (tries to fill bins closest to max weight)
        best_fit_bin = None
        min_remaining_space = float("inf")
        
        for i in range(len(bins)):
            remaining_space = max_bin_weight - bin_weights_gross[i]
            if (
                bin_weights_gross[i] + row["GrossWeight"] <= max_bin_weight and
                bin_items_count[i] < max_items_per_bin and
                remaining_space < min_remaining_space  # Prioritize bins that are closer to being full
            ):
                best_fit_bin = i
                min_remaining_space = remaining_space
        
        # Try placing in the bin assigned to the same truck (if exists & fits constraints)
        if truck in truck_bins:
            bin_idx = truck_bins[truck]
            if (
                bin_weights_gross[bin_idx] + row["GrossWeight"] <= max_bin_weight and 
                bin_items_count[bin_idx] < max_items_per_bin
            ):
                bins[bin_idx].append(index)
                bin_weights_gross[bin_idx] += row["GrossWeight"]
                bin_weights_nett[bin_idx] += row["NettWeight"]
                bin_items_count[bin_idx] += 1
                placed = True
        
        # If not placed, use the best-fit bin
        if not placed and best_fit_bin is not None:
            bins[best_fit_bin].append(index)
            bin_weights_gross[best_fit_bin] += row["GrossWeight"]
            bin_weights_nett[best_fit_bin] += row["NettWeight"]
            bin_items_count[best_fit_bin] += 1
            truck_bins[truck] = best_fit_bin  # Assign truck to this bin
            placed = True
        
        # If still not placed, create a new bin
        if not placed:
            bins.append([index])
            bin_weights_gross.append(row["GrossWeight"])
            bin_weights_nett.append(row["NettWeight"])
            bin_items_count.append(1)
            truck_bins[truck] = len(bins) - 1  # Assign the new bin to the truck
    
    # Assign bin numbers
    bin_assignment = {}
    for bin_number, bin_indices in enumerate(bins, start=1):
        for idx in bin_indices:
            bin_assignment[idx] = bin_number
    
    sorted_df["Bin"] = sorted_df.index.map(lambda idx: bin_assignment[idx])

    # Create summary table
    bin_summary = pd.DataFrame({
        "Bin": list(range(1, len(bins) + 1)),
        "Total GrossWeight": bin_weights_gross,
        "Total NettWeight": bin_weights_nett,
        "Items Count": bin_items_count
    })

    # Enforce min weight constraint: Flag bins below min weight
    bin_summary["Below Min Weight?"] = bin_summary["Total GrossWeight"] < min_bin_weight

    return sorted_df, bin_summary

# Streamlit UI
def main():
    st.title("Multi-Bin Packing Optimizer (Optimized Filling & Constraints)")

    # Sidebar
    st.sidebar.header("Upload Data & Settings")
    uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
    max_bin_weight = st.sidebar.number_input("Max Bin Weight", min_value=1, value=26500)
    min_bin_weight = st.sidebar.number_input("Min Bin Weight (for balance)", min_value=0, value=18000)
    max_items_per_bin = st.sidebar.number_input("Max Items per Bin", min_value=1, value=10)
    output_filename = st.sidebar.text_input("Output Excel File Name", "bin_packing_result.xlsx")

    if uploaded_file is not None:
        # Read Excel file
        df = pd.read_excel(uploaded_file, engine="openpyxl")

        # Check required columns
        required_columns = {"TruckNumber", "BundleNumber", "GrossWeight", "NettWeight"}
        if not required_columns.issubset(df.columns):
            st.error(f"Excel file must contain the following columns: {', '.join(required_columns)}")
            return
        
        # Display preview of the uploaded file
        st.subheader("Uploaded Data Preview")
        st.dataframe(df.head())

        # Process bin packing with constraints
        packed_df, bin_summary = pack_bins_optimized(df, max_bin_weight, min_bin_weight, max_items_per_bin)

        # Display results
        st.subheader("Packing Summary")
        st.write(f"**Total Bins Used:** {packed_df['Bin'].nunique()}")
        st.dataframe(bin_summary)

        # Save processed data in memory for download
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
            packed_df.to_excel(writer, index=False, sheet_name="Packed Data")
            bin_summary.to_excel(writer, index=False, sheet_name="Bin Summary")
        output_buffer.seek(0)

        # Download button
        st.download_button(
            label="Download Packed Data",
            data=output_buffer,
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()