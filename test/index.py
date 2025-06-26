
import os
from io import BytesIO
import openai
import json
import pandas as pd
from openai import AzureOpenAI

from dotenv import load_dotenv

load_dotenv()
# Step 1: Read the Excel file

try:
    school_df = pd.read_excel(
        r'C:\Users\msf-2\Documents\Projects\klickit-hackathon\test\student_sample.xlsx', engine='openpyxl')
    # Get the column names from the user's file
    user_column_headers = school_df.columns.tolist()
except Exception as e:
    # Handle cases where the file is not a valid Excel file
    print(f"Error reading Excel file: {e}")
    # Notify user of invalid file format


# Configure with your Azure credentials
# openai.api_type = "azure"
# # e.g., https://your-resource-name.openai.azure.com/
# openai.api_base = "YOUR_AZURE_ENDPOINT"
# openai.api_version = "2023-07-01-preview"
# openai.api_key = "YOUR_AZURE_OPENAI_KEY"
client = AzureOpenAI(
    api_key=os.getenv("GPT_3.5_TURBO_API_KEY"),
    azure_endpoint="https://cairo-hackathon-open-ai.openai.azure.com/",
    api_version="2024-02-01"
)

# The column headers from the user's uploaded file
user_column_headers = [f'"{col}"' for col in school_df.columns.tolist()]

# The columns your Klickit system needs
klickit_student_parent_columns = ["Student ID", "Student Name",
                                  "Parent ID", "Parent Name", "Parent Phone", "Parent Email"]
klickit_installment_columns_description = "Columns representing payment installments or fees (e.g., 'Tuition Fee', 'Bus Fee', 'Term 1')."

# The prompt for the AI
prompt = f"""
I have an Excel sheet from a school with the following column headers:
{user_column_headers}

My system requires data to be mapped to these specific fields:
- Student/Parent Fields: {klickit_student_parent_columns}
- Installment Fields: {klickit_installment_columns_description}
- Composite ID Field: A field containing both Parent and Student ID, like 'parent/student'.

Analyze the user's column headers and return a JSON object that maps the user's headers to my system's fields.
Your JSON response should have three keys: "student_parent_mapping", "installment_columns", and "composite_id_column".
- For "student_parent_mapping", the keys should be my system's fields and the values should be the corresponding user header.
- For "installment_columns", provide a list of the user headers that represent payments.
- For "composite_id_column", provide the user header that contains the combined ID.

If you cannot find a confident match for a field, use `null` as the value.

Example user header: "Guardian's phone" should map to "Parent Phone".
Example user header: "id_stud" should map to "Student ID".
Example user header: "Term 1 Fee" should be in the "installment_columns" list.
"""

# Make the API call
# response = openai.ChatCompletion.create(
#     engine="gpt-4",  # Or your preferred model deployment name
#     messages=[
#         {"role": "system", "content": "You are a helpful AI assistant that maps Excel columns to a defined schema and responds in JSON."},
#         {"role": "user", "content": prompt}
#     ],
#     temperature=0.0,
#     response_format={"type": "json_object"}  # Enforce JSON output
# )

response = client.chat.completions.create(
    model="gpt-35-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant that maps Excel columns to a defined schema and responds in JSON."},
        {"role": "user", "content": prompt}
    ]
)

# Extract and parse the JSON mapping
try:
    # print("AI Response:", response.choices[0].message.content)
    mapping = response.choices[0].message.content
    print("Raw AI Response:", mapping)
    # Parse the JSON string into a Python dictionary
    mapping = json.loads(mapping)
    print("AI Mapping Successful:", mapping)
except (json.JSONDecodeError, KeyError) as e:
    print(f"Error parsing AI response: {e}")
    # Handle the error, maybe ask the user to manually map

# handle missing data
report = []
required_fields = ["Student Name", "Parent Name"]  # Example
for field, user_col in mapping['student_parent_mapping'].items():
    if field in required_fields and user_col is None:
        report.append(
            f"CRITICAL: Could not find a column for '{field}'. Please map it manually.")
    print(f"Field: {field}, User Column: {user_col}")
    if user_col and school_df[user_col].isnull().any():
        missing_count = school_df[user_col].isnull().sum()
        report.append(
            f"WARNING: Found {missing_count} empty cells in the '{user_col}' column.")


# Identify duplicate
student_name_col = mapping['student_parent_mapping'].get('Student Name')
if student_name_col:
    duplicates = school_df[school_df.duplicated(
        subset=[student_name_col], keep=False)]
    if not duplicates.empty:
        report.append(
            f"WARNING: Found potential duplicate students: {duplicates[student_name_col].tolist()}")

# Parse Composite IDs:
composite_col = mapping.get('composite_id_column')
if composite_col:
    # The expand=True creates new columns
    school_df[['derived_parent_id', 'derived_student_id']
              ] = school_df[composite_col].str.split('/', expand=True, n=1)
    # Now you can use 'derived_parent_id' and 'derived_student_id'
    mapping['student_parent_mapping']['Parent ID'] = 'derived_parent_id'
    mapping['student_parent_mapping']['Student ID'] = 'derived_student_id'


# Step 4: Generate the Three Template Files
# Payment Template:

id_vars = []  # Columns to keep as identifiers (student/parent names/ids)
for klickit_col, user_col in mapping['student_parent_mapping'].items():
    if user_col:
        id_vars.append(user_col)

# "Melt" the DataFrame to turn installment columns into rows
payments_df = school_df.melt(
    id_vars=id_vars,
    value_vars=mapping['installment_columns'],
    # This new column will hold 'Term 1', 'Term 2', etc.
    var_name='Payment Name',
    value_name='Amount'      # This new column will hold the fee amount
)
# Remove rows where there was no fee (NaN amount)
payments_df.dropna(subset=['Amount'], inplace=True)
# Now you have a clean list of individual payments to create your 'payment' file from.


# Parent Template:
parent_cols_map = {
    'ParentID': mapping['student_parent_mapping'].get('Parent ID'),
    'ParentName': mapping['student_parent_mapping'].get('Parent Name'),
    'ParentPhone': mapping['student_parent_mapping'].get('Parent Phone'),
    'ParentEmail': mapping['student_parent_mapping'].get('Parent Email')
}
# Create a new df with the Klickit column names
parent_df = pd.DataFrame()
for klickit_name, user_name in parent_cols_map.items():
    if user_name:
        parent_df[klickit_name] = school_df[user_name]

# Drop duplicates to get a unique list of parents
parent_df.drop_duplicates(subset=['ParentID', 'ParentName'], inplace=True)


# Student with Parent Template:
student_parent_cols_map = {
    'StudentName': mapping['student_parent_mapping'].get('Student Name'),
    'ParentName': mapping['student_parent_mapping'].get('Parent Name'),
    # ... other relevant fields
}
student_parent_df = pd.DataFrame()
for klickit_name, user_name in student_parent_cols_map.items():
    if user_name:
        student_parent_df[klickit_name] = school_df[user_name]

# Logic to create the 'payment link'
# This might be a summary of payments assigned to the student


def get_payment_summary(row):
    student_name_col = mapping['student_parent_mapping']['Student Name']
    student_name = row[student_name_col]
    student_payments = payments_df[payments_df[student_name_col]
                                   == student_name]
    # Create a comma-separated list of "PaymentName:Amount"
    return ", ".join([f"{p['Payment Name']}:{p['Amount']}" for i, p in student_payments.iterrows()])


# Apply this logic to generate the payment link/summary
# Note: This might be slow on 6k rows. A more optimized `merge` or `join` is better.
# For simplicity here, we use apply.
student_parent_df['PaymentLink'] = school_df.apply(get_payment_summary, axis=1)

# Drop any duplicates from this file too
student_parent_df.drop_duplicates(subset=['StudentName'], inplace=True)


# Step 5: Present Results and Export Files
# To convert a dataframe to an Excel file in memory for download
output = BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    parent_df.to_excel(writer, sheet_name='Parents', index=False)
    payments_df.to_excel(writer, sheet_name='Payments', index=False)
    student_parent_df.to_excel(
        writer, sheet_name='Students_with_Parents', index=False)
# The 'output' BytesIO object can then be returned in a web response.
