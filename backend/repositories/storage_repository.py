from typing import List, Dict, Any
from supabase import Client


class StorageRepository:
    def __init__(
        self,
        supabase_client: Client,
        bucket_name: str = "post-media"
    ):
        self.supabase = supabase_client
        self.bucket_name = bucket_name

    async def upload_file(
        self,
        file_path: str,
        file_bytes: bytes,
        content_type: str
    ) -> None:
        """Uploads raw binary data to the storage bucket."""
        self.supabase.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "x-upsert": "true",
            },
        )

    def get_public_url(self, file_path: str) -> str:
        """Retrieves the public and permanent URL of the file."""
        # Note: In the Supabase Python client, get_public_url is generally synchronous.
        # It returns a string or a dict depending on the library version.
        res = self.supabase.storage.from_(self.bucket_name).get_public_url(
            file_path
        )

        # Handle the return format depending on the supabase-py version
        if isinstance(res, dict) and "publicUrl" in res:
            return res["publicUrl"]

        return getattr(res, "public_url", str(res))

    async def list_files(
        self,
        folder_path: str
    ) -> List[Dict[str, Any]]:
        """Lists files in a given folder path."""
        files = self.supabase.storage.from_(self.bucket_name).list(
            path=folder_path
        )

        return files or []