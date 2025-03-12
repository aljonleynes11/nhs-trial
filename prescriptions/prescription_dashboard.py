import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import os  

# 📊 NHS Prescription Data Dashboard
st.title("📊 NHS Dec 2024 Prescription Data Dashboard")

# Debugging: Show Current Directory & Available Files
st.subheader("🛠 Debugging Info")
current_dir = os.getcwd()
st.write("📂 Current Directory:", current_dir)

# List files in the directory
# all_files = os.listdir(current_dir)
# st.write("📂 Files in Directory:", all_files)

# 🔍 Search for Prescription CSV Files
data_files = glob.glob(os.path.join(current_dir, "prescription_cardio_and_diabetes_final.csv"))
st.write("🔍 Found CSV Files:", data_files)

# Handle No Files Found
if not data_files:
    st.error("🚨 No data files found! Ensure the CSV files are in the correct directory.")
    st.stop()

# ✅ Load & Merge CSV Files
try:
    df_list = [pd.read_csv(file) for file in data_files]
    df = pd.concat(df_list, ignore_index=True)
except Exception as e:
    st.error(f"❌ Error reading CSV files: {e}")
    st.stop()

# Drop YEAR_MONTH Column (if exists)
if "YEAR_MONTH" in df.columns:
    df.drop(columns=["YEAR_MONTH"], inplace=True)

# 🔍 Display Data Preview
st.subheader("🔍 Data Preview")
st.write(df.head())

# 📌 Filter by BNF Section
if "BNF_SECTION_CODE" in df.columns:
    st.subheader("📌 Filter Data by BNF Section")

    # Generate Section Mapping
    unique_sections = df["BNF_SECTION_CODE"].dropna().unique()
    section_mapping = {str(int(code)): f"Section {int(code)}" for code in unique_sections}

    # User Selection
    section_choice = st.selectbox("Select BNF Section:", ["All"] + list(section_mapping.values()))

    # Apply Filter
    df_filtered = df[df["BNF_SECTION_CODE"] == int([k for k, v in section_mapping.items() if v == section_choice][0])] if section_choice != "All" else df

    # 📄 Show Filtered Data
    st.subheader("📄 Filtered Data")
    st.write(df_filtered.head())

    # 📥 Download Button
    st.download_button(
        label="📥 Download Filtered Data",
        data=df_filtered.to_csv(index=False),
        file_name="filtered_nhs_data.csv",
        mime="text/csv"
    )

# 🌍 Top 10 Regions by Prescriptions
if "REGION_NAME" in df_filtered.columns:
    st.subheader("🌍 Top 10 Regions with Most Prescriptions")
    top_regions = df_filtered.groupby("REGION_NAME").agg({"NIC": "sum", "ITEMS": "sum"}).nlargest(10, "ITEMS").reset_index()
    top_regions.rename(columns={"NIC": "Net Ingredient Cost", "ITEMS": "Number Of Prescription Items Dispensed"}, inplace=True)

    st.write(top_regions)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=top_regions["Number Of Prescription Items Dispensed"], y=top_regions["REGION_NAME"], palette="Reds_r", ax=ax)
    ax.set_xlabel("Total Items Dispensed")
    ax.set_ylabel("Region Name")
    ax.set_title("Top 10 Regions by Prescriptions Dispensed")
    st.pyplot(fig)

# 📊 Top 10 Drugs by Cost & Items
if "BNF_CHEMICAL_SUBSTANCE" in df_filtered.columns and "NIC" in df_filtered.columns and "ITEMS" in df_filtered.columns:
    st.subheader("📊 Grouped Data by BNF Chemical Substance")
    grouped_data = df_filtered.groupby("BNF_CHEMICAL_SUBSTANCE").agg({"NIC": "sum", "ITEMS": "sum"}).reset_index()
    grouped_data.rename(columns={"NIC": "Net Ingredient Cost", "ITEMS": "Number Of Prescription Items Dispensed"}, inplace=True)

    st.write(grouped_data)

    # 💊 Top 10 Drugs by Cost
    st.subheader("💊 Top 10 Most Prescribed Drugs by Cost")
    top_drugs = grouped_data.nlargest(10, "Net Ingredient Cost")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=top_drugs["Net Ingredient Cost"], y=top_drugs["BNF_CHEMICAL_SUBSTANCE"], palette="Blues_r", ax=ax)
    ax.set_xlabel("Total NIC (£)")
    ax.set_ylabel("Drug Name")
    ax.set_title("Top 10 Most Prescribed Drugs by NIC")
    st.pyplot(fig)

    # 💊 Top 10 Drugs by Items Dispensed
    st.subheader("💊 Top 10 Most Prescribed Drugs by Items Dispensed")
    top_items = grouped_data.nlargest(10, "Number Of Prescription Items Dispensed")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=top_items["Number Of Prescription Items Dispensed"], y=top_items["BNF_CHEMICAL_SUBSTANCE"], palette="Greens_r", ax=ax)
    ax.set_xlabel("Total Items Dispensed")
    ax.set_ylabel("Drug Name")
    ax.set_title("Top 10 Most Prescribed Drugs by Items Dispensed")
    st.pyplot(fig)

# 🥧 Prescription Cost Distribution by BNF Section
if "BNF_CHEMICAL_SUBSTANCE" in df_filtered.columns and "NIC" in df_filtered.columns:
    st.subheader("🥧 Prescription Cost Distribution by BNF Section")

    section_costs = df_filtered.groupby("BNF_CHEMICAL_SUBSTANCE")["NIC"].sum().reset_index()
    top_sections = section_costs.nlargest(20, "NIC")
    top_sections["BNF_CHEMICAL_SUBSTANCE"] = top_sections["BNF_CHEMICAL_SUBSTANCE"].astype(str)
    top_sections.rename(columns={"BNF_CHEMICAL_SUBSTANCE": "BNF Section", "NIC": "Total Cost (£)"}, inplace=True)

    fig = px.pie(top_sections, values="Total Cost (£)", names="BNF Section", title="Top 20 BNF Sections by Prescription Cost", hole=0.3, color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig)

# 📦 Prescription Distribution by Unit of Measure (UOM)
if "UNIT_OF_MEASURE" in df_filtered.columns and "ITEMS" in df_filtered.columns:
    st.subheader("📦 Prescription Distribution by Unit of Measure")

    uom_distribution = df_filtered.groupby("UNIT_OF_MEASURE")["ITEMS"].sum().reset_index()
    top_uoms = uom_distribution.nlargest(10, "ITEMS")
    top_uoms.rename(columns={"UNIT_OF_MEASURE": "Unit of Measure", "ITEMS": "Total Items Dispensed"}, inplace=True)

    fig = px.pie(top_uoms, values="Total Items Dispensed", names="Unit of Measure", title="Top 10 Units of Measure by Items Dispensed", hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig)
