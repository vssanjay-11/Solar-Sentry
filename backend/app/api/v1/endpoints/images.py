from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status, Response

from app.schemas.image import (
    ImageMetadata,
    ImageUploadResponse,
    CameraType,
)
from app.services.image_service import ImageService
from app.api.deps import get_image_service

router = APIRouter(prefix="/images", tags=["Observatory Vision Ingestion"])


@router.post(
    "",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest camera snapshot frame"
)
async def upload_image(
    file: UploadFile = File(..., description="Binary JPEG/PNG image data"),
    device_id: str = Form(default="esp32-cam-01"),
    camera_type: CameraType = Form(default=CameraType.ESP32_CAM),
    pan: Optional[int] = Form(default=None),
    tilt: Optional[int] = Form(default=None),
    lux: Optional[float] = Form(default=None),
    service: ImageService = Depends(get_image_service)
) -> ImageUploadResponse:
    """Ingests image frame from ESP32-CAM or simulated camera node."""
    data = await file.read()
    content_type = file.content_type or "image/jpeg"
    return await service.ingest_image(
        data=data,
        device_id=device_id,
        camera_type=camera_type,
        pan=pan,
        tilt=tilt,
        lux=lux,
        content_type=content_type
    )


@router.get(
    "",
    response_model=List[ImageMetadata],
    summary="List metadata of captured images"
)
async def list_images(
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: ImageService = Depends(get_image_service)
) -> List[ImageMetadata]:
    return await service.list_images(device_id=device_id, limit=limit)


@router.get(
    "/{image_id}",
    response_model=ImageMetadata,
    summary="Get metadata and AI vision analysis for image"
)
async def get_image_metadata(
    image_id: str,
    service: ImageService = Depends(get_image_service)
) -> ImageMetadata:
    return await service.get_metadata(image_id)


@router.get(
    "/{image_id}/data",
    summary="Retrieve raw image binary bytes (JPEG/PNG)"
)
async def get_image_bytes(
    image_id: str,
    service: ImageService = Depends(get_image_service)
):
    metadata, data = await service.get_image_data(image_id)
    return Response(
        content=data,
        media_type=metadata.content_type,
        headers={"Content-Disposition": f"inline; filename={metadata.image_id}.jpg"}
    )
