import streamlit as st
import pandas as pd
from data_processor import process_file
from io import BytesIO


def to_excel(dfs):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for name, df in dfs.items():
            df.to_excel(writer, sheet_name=name, index=False)
    processed_data = output.getvalue()
    return processed_data


def main():
    st.set_page_config(
        layout="wide", page_title="School Data Onboarding AI Assistant")

    st.title("School Data Onboarding AI Assistant")

    st.markdown("""
    Welcome to the AI-powered onboarding assistant! 
    
    **How to use:**
    1.  Upload your unstructured Excel file (`.xls` or `.xlsx`).
    2.  The assistant will display the original data.
    3.  Click the "Process File" button.
    4.  The assistant will analyze the data, structure it into Parent, Student, and Payment sheets, and display the results.
    5.  Review the notifications for important information about the process.
    6.  Download the processed data as a new Excel file.
    """)

    uploaded_file = st.file_uploader(
        "Upload an Excel file", type=["xls", "xlsx"])

    if uploaded_file is not None:
        with st.expander("View Original Data"):
            try:
                df = pd.read_excel(
                    uploaded_file, engine='openpyxl' if uploaded_file.name.endswith('xlsx') else 'xlrd')
                st.dataframe(df)
            except Exception as e:
                st.error(
                    f"An error occurred while reading the Excel file: {e}")
                st.stop()

        if st.button("Process File"):
            with st.spinner('Processing your file... This may take a moment.'):
                try:
                    parent_df, student_df, payment_df, notifications = process_file(
                        df)

                    st.subheader("Processed Data")

                    with st.expander("Parent Data", expanded=True):
                        st.dataframe(parent_df)

                    with st.expander("Student Data", expanded=True):
                        st.dataframe(student_df)

                    with st.expander("Payment Data", expanded=True):
                        st.dataframe(payment_df)

                    st.subheader("Notifications & Warnings")
                    info_notifications = [
                        n for n in notifications if "Warning:" not in n]
                    warning_notifications = [
                        n for n in notifications if "Warning:" in n]

                    for notification in info_notifications:
                        st.info(notification)

                    for notification in warning_notifications:
                        st.warning(notification)

                    # --- Download Button ---
                    processed_dfs = {
                        "Parent": parent_df,
                        "Student": student_df,
                        "Payment": payment_df
                    }
                    excel_data = to_excel(processed_dfs)
                    st.download_button(
                        label="📥 Download Processed Excel File",
                        data=excel_data,
                        file_name="processed_school_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                except Exception as e:
                    st.error(f"An error occurred during processing: {e}")


if __name__ == "__main__":
    main()
