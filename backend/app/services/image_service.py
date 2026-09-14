import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from app.schemas.image import (
    ImageMetadata,
    ImageUploadResponse,
    CameraType,
)
from app.repositories.base import ImageRepository
from app.core.exceptions import ImageNotFoundError
from app.core.logging import logger


class ImageService:
    """Manages environmental vision capture storage and metadata retrieval."""

    def __init__(self, repository: ImageRepository):
        self.repository = repository

    async def ingest_image(
        self,
        data: bytes,
        device_id: str,
        camera_type: CameraType = CameraType.ESP32_CAM,
        pan: Optional[int] = None,
        tilt: Optional[int] = None,
        lux: Optional[float] = None,
        content_type: str = "image/jpeg"
    ) -> ImageUploadResponse:
        image_id = f"img-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        metadata = ImageMetadata(
            image_id=image_id,
            device_id=device_id,
            camera_type=camera_type,
            timestamp=now,
            pan=pan,
            tilt=tilt,
            lux=lux,
            content_type=content_type,
            file_size_bytes=len(data)
        )

        saved = await self.repository.save_image(metadata, data)
        logger.info(f"Ingested image '{image_id}' from device '{device_id}' ({len(data)} bytes)")

        return ImageUploadResponse(
            image_id=saved.image_id,
            device_id=saved.device_id,
            status="stored",
            timestamp=saved.timestamp,
            file_size_bytes=saved.file_size_bytes,
            url=f"/api/v1/images/{saved.image_id}/data"
        )

    async def get_metadata(self, image_id: str) -> ImageMetadata:
        meta = await self.repository.get_metadata(image_id)
        if not meta:
            raise ImageNotFoundError(image_id)
        return meta

    async def get_image_data(self, image_id: str) -> Tuple[ImageMetadata, bytes]:
        res = await self.repository.get_data(image_id)
        if not res:
            raise ImageNotFoundError(image_id)
        return res

    async def list_images(self, device_id: Optional[str] = None, limit: int = 50) -> List[ImageMetadata]:
        return await self.repository.list_images(device_id=device_id, limit=limit)

    async def attach_analysis(self, image_id: str, analysis: Dict[str, Any]) -> ImageMetadata:
        meta = await self.repository.update_analysis(image_id, analysis)
        if not meta:
            raise ImageNotFoundError(image_id)
        return meta
