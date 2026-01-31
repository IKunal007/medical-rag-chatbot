import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service(creds_path: str):
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def list_files_in_folder(service, folder_id: str):
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType)"
    ).execute()

    return results.get("files", [])


def download_file(service, file_id: str, out_path: str):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(out_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return out_path
