import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

credsPath = r"C:\Python\EngagementCalculator\engagementcalculator-fef079d955ba.json"
sheetID = r"1_SMHZEbGrT8MmSgH7hFLA9DuQ2zbf3i5GMREYh3ZnDM"

# Define the scope
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive"
]


# Add credentials
creds = Credentials.from_service_account_file(credsPath, scopes=scope)
# Authenticate and create the client
client = gspread.authorize(creds)


sheet = client.open_by_key(sheetID).sheet1

# Get all values in the sheet
all_values = sheet.get_all_values()

# Find the index of the "Youtube Links" column
header = all_values[0]  # first row is the header
col_index = header.index("Youtube Links")  # find the column position

# Extract all values from that column, skipping the header
youtube_links = [row[col_index] for row in all_values[1:]]

print(youtube_links)