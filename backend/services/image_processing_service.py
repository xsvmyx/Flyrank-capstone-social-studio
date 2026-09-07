import io
import uuid
from typing import Tuple
import httpx
from PIL import Image, ImageOps
from app.database import supabase_admin
from storage3.utils import StorageException
from config.settings import logger


class ImageProcessor:
    def __init__(self, bucket_name: str = "post-media"):
        """
        Initialize the ImageProcessor with a Supabase client and a bucket name.
        """
        self.supabase = supabase_admin
        self.bucket_name = bucket_name

    async def resize_and_upload(
        self,
        image_url: str,
        dimensions: Tuple[int, int],
        user_id: str,
        platform_name: str
    ) -> str:
        """
        Downloads an image from a URL, resizes/crops it to target dimensions,
        uploads the processed image to Supabase Storage, and returns its public or signed URL.

        :param image_url: Source URL or signed URL of the original image.
        :param dimensions: Target width and height tuple, e.g., (1080, 1080).
        :param user_id: ID of the user (for RLS path isolation).
        :param platform_name: Platform suffix for organization (e.g., 'instagram', 'linkedin').
        :return: URL of the processed image.
        """
        target_width, target_height = dimensions

        try:
            
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                if response.status_code != 200:
                    raise ValueError(f"Failed to fetch image from URL: Status {response.status_code}")
                image_bytes = response.content

            
            with Image.open(io.BytesIO(image_bytes)) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                
                processed_img = ImageOps.fit(
                    img,
                    (target_width, target_height),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )

                
                output_buffer = io.BytesIO()
                processed_img.save(output_buffer, format="JPEG", quality=85, optimize=True)
                output_bytes = output_buffer.getvalue()

            
            filename = f"{platform_name}_{uuid.uuid4()}.jpg"
            storage_path = f"{user_id}/processed/{filename}"

            
            self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=output_bytes,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )


            url_res = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            logger.info(f"✅ Image successfully resized to {dimensions} and saved at: {storage_path}")
            return url_res

        except StorageException as e:
            logger.error(f"❌ Supabase Storage error during image processing for user {user_id}: {e}")
            raise RuntimeError(f"Storage error: {e}")
        except Exception as e:
            logger.error(f"💥 Failed to process image for user {user_id} on platform {platform_name}: {e}")
            raise e