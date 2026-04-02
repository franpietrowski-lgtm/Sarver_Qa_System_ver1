from fastapi import APIRouter, Depends, HTTPException

from shared.deps import require_roles, get_storage_status_payload

router = APIRouter()


@router.get("/integrations/storage/status")
async def storage_status(user: dict = Depends(require_roles("management", "owner"))):
    return get_storage_status_payload()


@router.get("/integrations/drive/status")
async def drive_status(user: dict = Depends(require_roles("management", "owner"))):
    storage = get_storage_status_payload()
    return {**storage, "scope": [storage["bucket"]]}


@router.get("/integrations/drive/connect")
async def connect_drive(user: dict = Depends(require_roles("management", "owner"))):
    raise HTTPException(status_code=410, detail="Google Drive sync has been retired. Supabase Storage is active.")


@router.get("/oauth/drive/callback")
async def drive_callback(code: str, state: str):
    raise HTTPException(status_code=410, detail="Google Drive callback is no longer used. Supabase Storage is active.")
