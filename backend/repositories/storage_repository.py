from typing import List, Dict, Any
from supabase import Client



class StorageRepository:
    def __init__(self, supabase_client: Client, bucket_name: str = "post-media"):
        self.supabase = supabase_client
        self.bucket_name = bucket_name

    async def upload_file(self, file_path: str, file_bytes: bytes, content_type: str) -> None:
        """Uploads raw binary data to the storage bucket."""
        self.supabase.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "x-upsert": "true",
            },
        )

    async def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generates a signed temporary URL for accessing the file."""
        res = self.supabase.storage.from_(self.bucket_name).create_signed_url(
            path=file_path,
            expires_in=expires_in,
        )
        if isinstance(res, dict) and "signedUrl" in res:
            return res["signedUrl"]
        return getattr(res, "signed_url", str(res))

    async def list_files(self, folder_path: str) -> List[Dict[str, Any]]:
        """Lists files in a given folder path."""
        files = self.supabase.storage.from_(self.bucket_name).list(path=folder_path)
        return files or []