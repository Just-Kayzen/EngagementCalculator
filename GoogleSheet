import gspread
from google.oauth2.service_account import Credentials

# Define the scope for Google Sheets and Google Drive API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Path to your service account JSON key file
SERVICE_ACCOUNT_FILE = "service_account.json"

try:
    # Authenticate using the service account
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)

    # Open the Google Sheet by name or URL
    sheet = client.open("My Messages Sheet").sheet1  # First worksheet

    # Read all values from the sheet
    data = sheet.get_all_values()

    # Display messages (assuming first column contains messages)
    print("Messages from Google Sheet:")
    for row in data:
        if row:  # Skip empty rows
            print(row[0])

except FileNotFoundError:
    print("Error: service_account.json file not found.")
except gspread.SpreadsheetNotFound:
    print("Error: Google Sheet not found or access denied.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
