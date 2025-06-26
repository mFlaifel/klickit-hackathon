# Klickit Hackathon - Student Data Analyzer

## Overview

The Klickit Hackathon project is a web application designed to analyze student data from Excel files. It utilizes Streamlit for the user interface and Azure OpenAI for data processing and analysis.

## Features

- Upload messy student Excel files.
- Analyze and clean data using AI.
- Display structured data and notes on data quality.

## Requirements

To run this project, you need to install the following dependencies:

- `streamlit`
- `pandas`
- `openai`
- `python-dotenv`

## Installation

1. Clone the repository:

   ```
   git clone <repository-url>
   cd klickit-hackathon
   ```

2. Create a virtual environment (optional but recommended):

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

To start the application, run the following command:

```
streamlit run analyze.py
```

## Usage

1. Open your web browser and navigate to the URL provided by Streamlit (usually `http://localhost:8501`).
2. Upload your Excel file containing student data.
3. The application will analyze the data and display the cleaned results along with any notes or warnings.

## Contributing

Feel free to contribute to this project by submitting issues or pull requests.

## License

This project is licensed under the MIT License.
