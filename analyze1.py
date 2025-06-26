import streamlit as st
import pandas as pd
import json
from openai import AzureOpenAI
import os
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")

# Azure OpenAI client
client = AzureOpenAI(
    api_key=azure_openai_key,
    azure_endpoint="https://cairo-hackathon-open-ai.openai.azure.com/",
    api_version="2024-02-01"
)

st.set_page_config(page_title="Student Data Analyzer", layout="wide")

st.title("Smart Student Excel Analyzer")
st.write("Upload your messy student Excel file. The system will analyze, clean, and return structured data and notes.")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.subheader("Preview of Raw Excel Data")
        st.dataframe(df)

        # Prompts
        system_prompt = """
        You are a data analyst assistant. Your job is to:
        1. Analyze raw messy student Excel data.
        2. Extract clean structured data in JSON format under the key 'students',in column discount if the value is a string convert it to a number as a percentage.
        3. Generate any issues, alerts, or data quality suggestions under the key 'notes'.

        Respond ONLY in valid JSON like:
        {
          "students": [ ... ],
          "notes": [ "Issue 1", "Suggestion 2", ... ]
        }
        """

        user_prompt = f"""
        Analyze and clean the following raw data from Excel.
        Return JSON as described above.

        Raw data:
        {df.to_csv(index=False)}
        """

        # Call GPT model
        with st.spinner(" Analyzing data with GPT..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            result = response.choices[0].message.content.strip()

        # Try to parse JSON
        try:
            result_json = json.loads(result)
            students = result_json.get("students", [])
            notes = result_json.get("notes", [])

            st.success("Data successfully analyzed and cleaned!")

            if students:
                st.subheader("Cleaned Student Data")
                st.dataframe(pd.DataFrame(students))

            if notes:
                st.subheader("Notes & Warnings")
                for note in notes:
                    st.warning(note)
            else:
                st.info("No issues detected in the data.")

        except json.JSONDecodeError:
            st.error("Error: GPT response is not valid JSON.")
            st.code(result)

    except Exception as e:
        st.error(f"Failed to read file: {e}")
