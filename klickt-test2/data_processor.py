import pandas as pd
import re
import random
import string
import numpy as np

# --- Column Keywords ---
PARENT_KEYWORDS = {
    'Parent ID': ['parent id', 'parentid', 'parent_id'],
    'First Name': ['first name', 'fname', 'parent first name', 'father name'],
    'Last Name': ['last name', 'lname', 'parent last name', 'family name'],
    'Phone': ['phone', 'mobile', 'contact', 'phone number'],
    'Email': ['email', 'e-mail'],
    'Password': ['password']
}

STUDENT_KEYWORDS = {
    'parentid': ['parent id', 'parentid'],
    'StudentID': ['student id', 'studentid', 'student_id'],
    'grade': ['grade', 'class'],
    'Name': ['student name', 'studentname', 'name', 'full name'],
    'Payments': ['payments', 'fees', 'installments'],
    'Discount Name': ['discount name', 'discount'],
    'Discount Payment': ['discount payment'],
    'Deadline': ['deadline', 'due date']
}

PAYMENT_KEYWORDS = {
    'ID': ['payment id', 'fee id', 'id'],
    'Payment Name': ['payment name', 'fee name', 'installment name', 'name'],
    'Amount': ['amount', 'price', 'cost'],
    'AcademicYear': ['academic year', 'year'],
    'dueDate': ['due date', 'deadline']
}


def find_column_mapping(df_columns, keywords):
    """
    Finds the best mapping from dataframe columns to keyword-defined columns.
    """
    mapping = {}
    unmapped_columns = list(df_columns)

    for target_col, keys in keywords.items():
        for key in keys:
            for col in unmapped_columns:
                # Simple matching (case-insensitive, ignores spaces and underscores)
                if re.sub(r'[\s_]', '', col).lower() == re.sub(r'[\s_]', '', key).lower():
                    mapping[target_col] = col
                    unmapped_columns.remove(col)
                    break
            if target_col in mapping:
                break
    return mapping


def extract_installment_payments(df, payment_schema, notifications):
    """
    Finds and extracts installment payments from columns.
    """
    installment_cols = [col for col in df.columns if re.match(
        r'(installment|term|q)\s*\d+', col, re.IGNORECASE)]

    if not installment_cols:
        return []

    notifications.append(
        f"Found installment-like columns: {installment_cols}. Unpivoting them into payment records.")

    id_vars = [col for col in df.columns if 'id' in col.lower()
               and col not in installment_cols]
    if not id_vars:
        # If no clear ID column, use the first column as a default ID
        id_vars = [df.columns[0]]
        notifications.append(
            f"Warning: No clear ID column found for payments. Using '{id_vars[0]}' as a reference ID.")

    melted_df = df.melt(id_vars=id_vars, value_vars=installment_cols,
                        var_name='Payment Name', value_name='Amount')

    # Drop rows where amount is NaN or zero, as they don't represent a real payment
    melted_df.dropna(subset=['Amount'], inplace=True)
    melted_df = melted_df[melted_df['Amount'] > 0]

    if melted_df.empty:
        return installment_cols

    num_new_payments = len(melted_df)

    # Populate payment schema for all keys to ensure equal length
    for key in PAYMENT_KEYWORDS.keys():
        if key == 'ID':
            start_id = len(payment_schema.get('ID', []))
            payment_schema['ID'].extend(
                range(start_id, start_id + num_new_payments))
        elif key == 'Payment Name':
            payment_schema['Payment Name'].extend(melted_df['Payment Name'])
        elif key == 'Amount':
            payment_schema['Amount'].extend(melted_df['Amount'])
        else:
            payment_schema[key].extend([np.nan] * num_new_payments)

    return installment_cols


def handle_combined_id_column(df, student_mapping, notifications):
    """
    Checks for and handles a combined parent/student ID column.
    """
    # Attempt to find a combined ID column if standard IDs are not mapped
    if 'parentid' not in student_mapping and 'StudentID' not in student_mapping:
        for col in df.columns:
            if 'id' in col.lower() and df[col].astype(str).str.contains('/').any():
                notifications.append(
                    f"Found a combined ID column: '{col}'. Splitting into Parent and Student IDs.")

                # Split the column and assign to mapping
                df[['generated_parent_id', 'generated_student_id']] = df[col].astype(
                    str).str.split('/', expand=True, n=1)
                student_mapping['parentid'] = 'generated_parent_id'
                student_mapping['StudentID'] = 'generated_student_id'
                return df  # Return modified df
    return df


def process_file(df):
    """
    This function will process the uploaded excel file.
    """
    notifications = []

    # --- Schema Definition ---
    parent_schema = {col: [] for col in PARENT_KEYWORDS.keys()}
    student_schema = {col: [] for col in STUDENT_KEYWORDS.keys()}
    payment_schema = {col: [] for col in PAYMENT_KEYWORDS.keys()}

    # --- Pre-process payments from columns ---
    processed_payment_cols = extract_installment_payments(
        df, payment_schema, notifications)

    # Filter out the processed payment columns from the main df to avoid re-processing
    df_main = df.drop(columns=processed_payment_cols)

    # --- Column Mapping ---
    parent_mapping = find_column_mapping(df_main.columns, PARENT_KEYWORDS)
    student_mapping = find_column_mapping(df_main.columns, STUDENT_KEYWORDS)
    payment_mapping = find_column_mapping(df_main.columns, PAYMENT_KEYWORDS)

    # --- Handle Combined ID Column ---
    df_main = handle_combined_id_column(
        df_main, student_mapping, notifications)

    notifications.append(f"Parent column mapping: {parent_mapping}")
    notifications.append(f"Student column mapping: {student_mapping}")
    notifications.append(f"Payment column mapping: {payment_mapping}")

    # --- Data Extraction and Population ---
    for index, row in df_main.iterrows():
        # Parent Data
        for target_col in PARENT_KEYWORDS.keys():
            if target_col in parent_mapping:
                parent_schema[target_col].append(
                    row[parent_mapping[target_col]])
            else:
                parent_schema[target_col].append(np.nan)

        # Student Data
        for target_col in STUDENT_KEYWORDS.keys():
            if target_col in student_mapping:
                student_schema[target_col].append(
                    row[student_mapping[target_col]])
            else:
                student_schema[target_col].append(np.nan)

        # Payment Data (if not handled by installment extraction)
        if not processed_payment_cols:
            for target_col in PAYMENT_KEYWORDS.keys():
                if target_col in payment_mapping:
                    payment_schema[target_col].append(
                        row[payment_mapping[target_col]])
                else:
                    payment_schema[target_col].append(np.nan)

    # --- Create DataFrames ---
    parent_df = pd.DataFrame(parent_schema)
    student_df = pd.DataFrame(student_schema)
    payment_df = pd.DataFrame(payment_schema)

    # --- Data Cleaning and Deduplication ---
    if 'Parent ID' in parent_df.columns:
        # Generate random passwords for parents with missing passwords
        if 'Password' in parent_df.columns:
            missing_pass_mask = parent_df['Password'].isnull() | (
                parent_df['Password'] == '')
            num_missing = missing_pass_mask.sum()
            if num_missing > 0:
                random_passwords = [''.join(random.choices(
                    string.ascii_letters + string.digits, k=8)) for _ in range(num_missing)]
                parent_df.loc[missing_pass_mask, 'Password'] = random_passwords
                notifications.append(
                    f"Generated random passwords for {num_missing} parents.")

        parent_df.drop_duplicates(subset=['Parent ID'], inplace=True)
        notifications.append("Removed duplicate parents based on 'Parent ID'.")

    if 'StudentID' in student_df.columns and not student_df['StudentID'].isnull().all():
        # Handle comma-separated payments
        if 'Payments' in student_df.columns:
            student_df['Payments'] = student_df['Payments'].astype(
                str).str.split(',').str.join(', ')
            notifications.append(
                "Processed comma-separated payment assignments for students.")

        student_df.drop_duplicates(subset=['StudentID'], inplace=True)
        notifications.append(
            "Removed duplicate students based on 'StudentID'.")

    if 'ID' in payment_df.columns and not payment_df['ID'].isnull().all():
        payment_df.drop_duplicates(subset=['ID'], inplace=True)
        notifications.append("Removed duplicate payments based on 'ID'.")

    # --- Notifications for unmapped columns ---
    for schema_name, mapping, keywords in [('Parent', parent_mapping, PARENT_KEYWORDS),
                                           ('Student', student_mapping,
                                            STUDENT_KEYWORDS),
                                           ('Payment', payment_mapping, PAYMENT_KEYWORDS)]:
        for key in keywords:
            if key not in mapping:
                notifications.append(
                    f"Warning: Could not find a column for '{key}' in the {schema_name} data. This field will be empty.")

    return parent_df, student_df, payment_df, notifications
