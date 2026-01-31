from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

creds = Credentials.from_service_account_file(
    "app/integrations/credentials.json",
    scopes=SCOPES
)

service = build("drive", "v3", credentials=creds)

FOLDER_ID = "1Ccz5XU9YTMHf9xxIpN7q3T8DYIqU9-ZW"

results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)"
).execute()

print(results.get("files", []))
