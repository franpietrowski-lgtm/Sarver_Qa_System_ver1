import io
import json
import logging
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/drive"]


def is_drive_configured() -> bool:
    return bool(
        os.environ.get("GOOGLE_CLIENT_ID")
        and os.environ.get("GOOGLE_CLIENT_SECRET")
        and os.environ.get("GOOGLE_DRIVE_REDIRECT_URI")
        and os.environ.get("DRIVE_TOKEN_ENCRYPTION_KEY")
    )


def _fernet() -> Fernet:
    return Fernet(os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"].encode())


def encrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().decrypt(value.encode()).decode()


def _client_config() -> dict:
    return {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ["GOOGLE_DRIVE_REDIRECT_URI"]],
        }
    }


def build_oauth_flow(state: str) -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=os.environ["GOOGLE_DRIVE_REDIRECT_URI"],
        state=state,
    )


def get_authorization_url(user_id: str) -> str:
    flow = build_oauth_flow(user_id)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=user_id,
    )
    return authorization_url


def credentials_to_document(credentials: Credentials, user_id: str) -> dict:
    return {
        "user_id": user_id,
        "access_token": encrypt_token(credentials.token),
        "refresh_token": encrypt_token(credentials.refresh_token),
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": encrypt_token(credentials.client_secret),
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }


def credentials_from_document(document: dict) -> Credentials:
    expiry = document.get("expiry")
    return Credentials(
        token=decrypt_token(document.get("access_token")),
        refresh_token=decrypt_token(document.get("refresh_token")),
        token_uri=document["token_uri"],
        client_id=document["client_id"],
        client_secret=decrypt_token(document.get("client_secret")),
        scopes=document.get("scopes", SCOPES),
        expiry=datetime.fromisoformat(expiry) if expiry else None,
    )


async def get_drive_service(db):
    if not is_drive_configured():
        return None, None

    credential_doc = await db.drive_credentials.find_one(
        {"is_active": True}, {"_id": 0}, sort=[("updated_at", -1)]
    )
    if not credential_doc:
        credential_doc = await db.drive_credentials.find_one({}, {"_id": 0}, sort=[("updated_at", -1)])
    if not credential_doc:
        return None, None

    credentials = credentials_from_document(credential_doc)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        await db.drive_credentials.update_one(
            {"user_id": credential_doc["user_id"]},
            {
                "$set": {
                    "access_token": encrypt_token(credentials.token),
                    "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    return service, credential_doc["user_id"]


def ensure_folder(service, name: str, parent_id: str | None = None) -> str:
    safe_name = name.replace("'", "\\'")
    parent_query = f" and '{parent_id}' in parents" if parent_id else ""
    query = (
        "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        f" and name = '{safe_name}'{parent_query}"
    )
    result = service.files().list(q=query, fields="files(id,name)", pageSize=1).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    created = service.files().create(body=metadata, fields="id").execute()
    return created["id"]


def upload_bytes(service, folder_id: str, filename: str, content: bytes, mime_type: str) -> str:
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    metadata = {"name": filename, "parents": [folder_id]}
    result = service.files().create(body=metadata, media_body=media, fields="id").execute()
    return result["id"]


async def sync_submission_bundle(db, submission: dict) -> dict:
    service, connected_user_id = await get_drive_service(db)
    if not service:
        return {"status": "pending_configuration"}

    year = datetime.now(timezone.utc).strftime("%Y")
    division = submission.get("division") or "Unassigned"
    service_type = submission.get("service_type") or "unspecified"
    job_identifier = submission.get("job_id") or submission.get("matched_job_id") or "unmatched"
    submission_folder_name = f"{job_identifier}_{submission['id']}"

    root_id = ensure_folder(service, "QA")
    year_id = ensure_folder(service, year, root_id)
    division_id = ensure_folder(service, division, year_id)
    service_type_id = ensure_folder(service, service_type, division_id)
    submission_folder_id = ensure_folder(service, submission_folder_name, service_type_id)

    for file_meta in submission.get("photo_files", []):
        file_path = file_meta.get("local_path")
        if not file_path or not os.path.exists(file_path):
            continue
        with open(file_path, "rb") as file_handle:
            upload_bytes(
                service,
                submission_folder_id,
                file_meta["filename"],
                file_handle.read(),
                file_meta.get("mime_type", "application/octet-stream"),
            )

    bundle_folder = submission.get("local_folder_path")
    if bundle_folder and os.path.isdir(bundle_folder):
        for filename in os.listdir(bundle_folder):
            if not filename.endswith(".json"):
                continue
            file_path = os.path.join(bundle_folder, filename)
            with open(file_path, "rb") as file_handle:
                upload_bytes(service, submission_folder_id, filename, file_handle.read(), "application/json")

    await db.submissions.update_one(
        {"id": submission["id"]},
        {
            "$set": {
                "drive_sync_status": "synced",
                "drive_folder_id": submission_folder_id,
                "drive_connected_user_id": connected_user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    logger.info("Submission %s synced to Google Drive", submission["id"])
    return {"status": "synced", "folder_id": submission_folder_id}


def dump_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, indent=2).encode()