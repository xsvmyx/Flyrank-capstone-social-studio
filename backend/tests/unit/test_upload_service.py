from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from postgrest.exceptions import APIError
from repositories.storage_repository import StorageRepository
from services.upload_service import UploadService
from storage3.utils import StorageException


@pytest.fixture
def mock_storage_repo():
    repo = MagicMock(spec=StorageRepository)
    repo.upload_file = AsyncMock()
    repo.get_signed_url = AsyncMock(return_value="https://storage.example.com/signed/photo.png")
    repo.list_files = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def upload_service(mock_storage_repo):
    return UploadService(storage_repo=mock_storage_repo)


def create_mock_upload_file(filename: str, content_type: str, content: bytes = b"fake-image-bytes"):
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.read = AsyncMock(return_value=content)
    return mock_file


# ==========================================
# 1. Tests for upload_image
# ==========================================

@pytest.mark.asyncio
async def test_upload_image_success(upload_service, mock_storage_repo):
    file = create_mock_upload_file(filename="avatar.png", content_type="image/png")
    user_id = "user_123"

    signed_url = await upload_service.upload_image(file=file, user_id=user_id)

    assert signed_url == "https://storage.example.com/signed/photo.png"
    mock_storage_repo.upload_file.assert_called_once()
    
    call_kwargs = mock_storage_repo.upload_file.call_args[1]
    assert call_kwargs["file_bytes"] == b"fake-image-bytes"
    assert call_kwargs["content_type"] == "image/png"
    assert call_kwargs["file_path"].startswith("user_123/")
    assert call_kwargs["file_path"].endswith(".png")

    mock_storage_repo.get_signed_url.assert_called_once()


@pytest.mark.asyncio
async def test_upload_image_unsupported_format(upload_service):
    file = create_mock_upload_file(filename="document.pdf", content_type="application/pdf")

    with pytest.raises(HTTPException) as exc_info:
        await upload_service.upload_image(file=file, user_id="user_123")

    assert exc_info.value.status_code == 400
    assert "Unsupported image format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_image_storage_exception(upload_service, mock_storage_repo):
    file = create_mock_upload_file(filename="photo.jpg", content_type="image/jpeg")
    mock_storage_repo.upload_file.side_effect = StorageException("Bucket limit reached")

    with pytest.raises(HTTPException) as exc_info:
        await upload_service.upload_image(file=file, user_id="user_123")

    assert exc_info.value.status_code == 400
    assert "Storage error: Bucket limit reached" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_image_api_error(upload_service, mock_storage_repo):
    file = create_mock_upload_file(filename="photo.webp", content_type="image/webp")
    
    api_error = APIError({"message": "Permission denied", "code": "403"})
    mock_storage_repo.upload_file.side_effect = api_error

    with pytest.raises(HTTPException) as exc_info:
        await upload_service.upload_image(file=file, user_id="user_123")

    assert exc_info.value.status_code == 400
    assert "Supabase API error: Permission denied" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_image_unexpected_exception(upload_service, mock_storage_repo):
    file = create_mock_upload_file(filename="photo.gif", content_type="image/gif")
    mock_storage_repo.upload_file.side_effect = Exception("Unexpected connection drop")

    with pytest.raises(HTTPException) as exc_info:
        await upload_service.upload_image(file=file, user_id="user_123")

    assert exc_info.value.status_code == 500
    assert "An internal server error occurred" in exc_info.value.detail


# ==========================================
# 2. Tests for list_user_uploads
# ==========================================

@pytest.mark.asyncio
async def test_list_user_uploads_success(upload_service, mock_storage_repo):
    mock_storage_repo.list_files.return_value = [
        {"name": "file1.png", "id": "id-1"},
        {"name": ".emptyFolderPlaceholder", "id": "id-2"},
        {"name": "file2.jpg", "id": "id-3"},
        {"name": "invalid_no_id"},
        {"name": "", "id": "id-4"},
    ]

    result = await upload_service.list_user_uploads(user_id="user_456")

    mock_storage_repo.list_files.assert_called_once_with(folder_path="user_456")
    assert result == ["user_456/file1.png", "user_456/file2.jpg"]


@pytest.mark.asyncio
async def test_list_user_uploads_failure(upload_service, mock_storage_repo):
    mock_storage_repo.list_files.side_effect = Exception("Database down")

    with pytest.raises(HTTPException) as exc_info:
        await upload_service.list_user_uploads(user_id="user_456")

    assert exc_info.value.status_code == 500
    assert "Failed to list your files." in exc_info.value.detail
