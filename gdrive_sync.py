import os
import io
import pandas as pd
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return Path(base_path) / relative_path

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = resource_path('gdrive_credentials.json')

def sync_csv_to_gdrive(local_csv_path: str, folder_id: str):
    if not os.path.exists(local_csv_path) or not SERVICE_ACCOUNT_FILE.exists():
        print(f"[GDrive] Missing local CSV or credentials. Skipping sync.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        file_name = Path(local_csv_path).name

        # Check if file exists in the cloud folder
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])

        local_df = pd.read_csv(local_csv_path)

        if not items:
            # Create new file
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            media = MediaFileUpload(local_csv_path, mimetype='text/csv')
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f">>> [GDrive] Uploaded new database to cloud. ID: {file.get('id')}")
        else:
            # Download cloud file
            file_id = items[0]['id']
            print(f">>> [GDrive] Found cloud database. Merging and syncing...")
            
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            try:
                cloud_df = pd.read_csv(fh)
            except pd.errors.EmptyDataError:
                cloud_df = pd.DataFrame()
            
            from googleapiclient.http import MediaIoBaseUpload
            
            # Merge cloud and local, drop exact duplicates
            if not cloud_df.empty:
                merged_df = pd.concat([cloud_df, local_df], ignore_index=True)
                merged_df.drop_duplicates(inplace=True)
            else:
                merged_df = local_df
            
            # Upload updated file via memory, DO NOT save to local_csv_path
            out_fh = io.StringIO()
            merged_df.to_csv(out_fh, index=False)
            out_fh.seek(0)
            
            media = MediaIoBaseUpload(io.BytesIO(out_fh.getvalue().encode('utf-8')), mimetype='text/csv')
            service.files().update(fileId=file_id, media_body=media).execute()
            
            print(f">>> [GDrive] Cloud and local databases successfully synced!")

    except Exception as e:
        print(f"[!] GDrive Error: Failed to sync to Google Drive: {e}")
