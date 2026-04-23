import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

credsPath = r"C:\Python\EngagementCalculator\engagementcalculator-fef079d955ba.json"
sheetName = r"ReadThis"


# Define the scope
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive"
]


# Add credentials
creds = Credentials.from_service_account_file(credsPath, scopes=scope)

# Authenticate and create the client
client = gspread.authorize(creds)

# Open the spreadsheet
sheet = client.open(sheetName).sheet1

sheet = client.open_by_key(r"1_SMHZEbGrT8MmSgH7hFLA9DuQ2zbf3i5GMREYh3ZnDM").sheet1
print(sheet.get_all_records())