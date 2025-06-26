from openai import AzureOpenAI

# Initialize the client

import pandas as pd

df = pd.read_excel("./Student_Data_Synthetic_1.xlsx")

client = AzureOpenAI(
    api_key="",
    azure_endpoint="https://cairo-hackathon-open-ai.openai.azure.com/",
    api_version="2024-02-01"
)

# print("Data loaded successfully. Here's a preview:", df.head().to_string())
response = client.chat.completions.create(
    model="gpt-35-turbo",
    messages=[
        {"role": "system", "content": "check if each student has a unique Id and valid last name and first name. if not create a new column with the first name and last name combined from name column  and print the new output in formatted tables."},
        {"role": "user", "content": f"Analyze this csv data:\n{df.head().to_string()} and provide insights on the data."}
    ]
)


# Access the response
print(response.choices[0].message.content)
print("Response from the model:")
print(response)
