"""
Solar Sentry — Camera / Optical Vision API Endpoints
Module: Agent 1 (ESP32-CAM), Agent 2 (Backend API), Agent 5 (Computer Vision)
"""

import asyncio
import base64
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.providers import provider_manager, SystemMode
from app.services.camera_calibration import (
    CameraCalibrationService,
    CalibrationParams,
    OpticalQualityEngine
)


router = APIRouter(prefix="/camera", tags=["Camera & Optical Vision"])

# Global in-memory cache for latest frames
_latest_raw_frame: Optional[bytes] = None
_latest_processed_frame: Optional[bytes] = None
_latest_metrics: Optional[Dict[str, Any]] = None
_latest_vision_summary: Optional[Dict[str, Any]] = None


class CameraConfigPayload(BaseModel):
    esp32_cam_url: str = Field(..., description="Target ESP32-CAM URL (e.g. http://192.168.1.120)")


class CalibrationRequest(BaseModel):
    brightness: int = Field(default=0, ge=-100, le=100)
    contrast: float = Field(default=1.0, ge=0.5, le=3.0)
    gamma: float = Field(default=1.0, ge=0.2, le=2.5)
    sharpness: float = Field(default=0.0, ge=0.0, le=100.0)
    saturation: float = Field(default=100.0, ge=0.0, le=200.0)
    noise_reduction: int = Field(default=0, ge=0, le=10)
    apply_clahe: bool = Field(default=False)
    clahe_clip_limit: float = Field(default=2.0, ge=0.5, le=5.0)
    normalize_hist: bool = Field(default=False)
    invert_colors: bool = Field(default=False)
    rotation_deg: int = Field(default=0)


from fastapi.responses import StreamingResponse
from app.services.camera_discovery import camera_registry


@router.get("/status", summary="Get camera connection state and metadata")
async def get_camera_status() -> Dict[str, Any]:
    status_info = await provider_manager.camera_provider.get_status()
    reg_info = camera_registry.get_info()
    status_info["system_mode"] = provider_manager.mode.value
    status_info["configured_url"] = provider_manager.camera_url
    status_info["registry"] = reg_info
    status_info["discovered_ip"] = reg_info.get("ip")
    status_info["hostname"] = reg_info.get("hostname")
    status_info["discovery_status"] = reg_info.get("status")
    status_info["discovery_method"] = reg_info.get("discovery_method")
    status_info["stream_url"] = "/api/v1/camera/stream"
    return status_info


@router.get("/discover", summary="Trigger dynamic mDNS / network discovery of ESP32-CAM")
async def discover_camera(fallback_ip: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    return await camera_registry.discover(fallback_ip=fallback_ip)


@router.get("/stream", summary="Live MJPEG video stream with dynamic camera proxying")
async def get_live_stream() -> StreamingResponse:
    async def frame_generator():
        while True:
            try:
                if provider_manager.mode == SystemMode.DEMO:
                    frame_bytes = await provider_manager.demo_camera.capture_raw_frame()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame_bytes)).encode("ascii") + b"\r\n\r\n" +
                        frame_bytes + b"\r\n"
                    )
                    await asyncio.sleep(0.08)  # ~12 FPS
                else:
                    # In HARDWARE mode
                    if camera_registry.status != "ONLINE":
                        await camera_registry.discover()

                    if camera_registry.status == "ONLINE" and camera_registry.current_ip:
                        try:
                            frame_bytes = await provider_manager.esp32_camera.capture_raw_frame()
                            yield (
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: " + str(len(frame_bytes)).encode("ascii") + b"\r\n\r\n" +
                                frame_bytes + b"\r\n"
                            )
                            await asyncio.sleep(0.066)  # ~15 FPS
                        except Exception as e:
                            logger.warning(f"Hardware camera frame fetch failed: {e}. Attempting rediscovery...")
                            await camera_registry.discover()
                            await asyncio.sleep(1.0)
                    else:
                        await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream generator error: {e}")
                await asyncio.sleep(1.0)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.post("/config", summary="Configure and validate ESP32-CAM target URL")
async def configure_camera_url(payload: CameraConfigPayload) -> Dict[str, Any]:
    url = provider_manager.set_camera_url(payload.esp32_cam_url)
    host = payload.esp32_cam_url.replace("http://", "").replace("https://", "").split(":")[0]
    await camera_registry.discover(fallback_ip=host)
    test_res = await provider_manager.esp32_camera.test_connection()
    return {
        "status": "CONFIGURED",
        "camera_url": url,
        "test_result": test_res,
        "registry": camera_registry.get_info()
    }


@router.get("/test", summary="Execute connection handshake to ESP32-CAM")
async def test_camera_connection() -> Dict[str, Any]:
    return await provider_manager.camera_provider.test_connection()


@router.get("/capture", summary="Capture raw optical frame")
@router.post("/capture", summary="Capture raw optical frame")
async def capture_frame(condition: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    global _latest_raw_frame, _latest_processed_frame, _latest_metrics, _latest_vision_summary
    try:
        # If in DEMO mode and condition specified, generate synthetic condition frame
        if provider_manager.mode == SystemMode.DEMO and condition:
            from ai.vision.preprocessor import generate_synthetic_solar_image
            import cv2
            cond_img = generate_synthetic_solar_image(condition=condition)
            ok, enc = cv2.imencode(".jpg", cond_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            raw_bytes = enc.tobytes() if ok else await provider_manager.camera_provider.capture_raw_frame()
        else:
            raw_bytes = await provider_manager.camera_provider.capture_raw_frame()

        _latest_raw_frame = raw_bytes

        # Auto-evaluate baseline calibration
        default_params = CameraCalibrationService.auto_enhance_params()
        proc_bytes, metrics, vis_summary = CameraCalibrationService.process_image(raw_bytes, default_params)
        _latest_processed_frame = proc_bytes
        _latest_metrics = metrics
        _latest_vision_summary = vis_summary

        b64_raw = base64.b64encode(raw_bytes).decode("utf-8")
        b64_proc = base64.b64encode(proc_bytes).decode("utf-8")
        composite_score = metrics.get("composite_score", 85.0)

        return {
            "status": "SUCCESS",
            "byte_size": len(raw_bytes),
            "raw_image_data": f"data:image/jpeg;base64,{b64_raw}",
            "processed_image_data": f"data:image/jpeg;base64,{b64_proc}",
            "image_base64": f"data:image/jpeg;base64,{b64_raw}",
            "raw_base64": f"data:image/jpeg;base64,{b64_raw}",
            "processed_base64": f"data:image/jpeg;base64,{b64_proc}",
            "quality_score": composite_score,
            "quality_metrics": metrics,
            "scorecard": metrics,
            "vision_analysis": vis_summary,
            "metadata": {
                "condition": condition or "clear",
                "width": 640,
                "height": 480
            },
            "system_mode": provider_manager.mode.value
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Camera frame acquisition failed: {e}"
        )


@router.get("/raw.jpg", summary="Download or stream latest raw image frame")
async def get_raw_image() -> Response:
    global _latest_raw_frame
    if _latest_raw_frame is None:
        # Generate initial frame
        _latest_raw_frame = await provider_manager.camera_provider.capture_raw_frame()
    return Response(content=_latest_raw_frame, media_type="image/jpeg")


@router.get("/processed.jpg", summary="Download or stream latest processed image frame")
async def get_processed_image() -> Response:
    global _latest_processed_frame
    if _latest_processed_frame is None:
        await capture_frame()
    assert _latest_processed_frame is not None
    return Response(content=_latest_processed_frame, media_type="image/jpeg")


@router.post("/calibrate", summary="Apply optical calibration and calculate image quality metrics")
async def calibrate_image(req: CalibrationRequest) -> Dict[str, Any]:
    global _latest_raw_frame, _latest_processed_frame, _latest_metrics, _latest_vision_summary
    if _latest_raw_frame is None:
        _latest_raw_frame = await provider_manager.camera_provider.capture_raw_frame()

    params = CalibrationParams(
        brightness=req.brightness,
        contrast=req.contrast,
        gamma=req.gamma,
        sharpness=req.sharpness,
        saturation=req.saturation,
        noise_reduction=req.noise_reduction,
        apply_clahe=req.apply_clahe,
        clahe_clip_limit=req.clahe_clip_limit,
        normalize_hist=req.normalize_hist,
        invert_colors=req.invert_colors,
        rotation_deg=req.rotation_deg
    )

    proc_bytes, metrics, vis_summary = CameraCalibrationService.process_image(_latest_raw_frame, params)
    _latest_processed_frame = proc_bytes
    _latest_metrics = metrics
    _latest_vision_summary = vis_summary

    b64_raw = base64.b64encode(_latest_raw_frame).decode("utf-8")
    b64_proc = base64.b64encode(proc_bytes).decode("utf-8")
    composite_score = metrics.get("composite_score", 85.0)

    return {
        "status": "SUCCESS",
        "raw_image_data": f"data:image/jpeg;base64,{b64_raw}",
        "raw_base64": f"data:image/jpeg;base64,{b64_raw}",
        "processed_image_data": f"data:image/jpeg;base64,{b64_proc}",
        "processed_base64": f"data:image/jpeg;base64,{b64_proc}",
        "quality_score": composite_score,
        "quality_metrics": metrics,
        "scorecard": metrics,
        "vision_analysis": vis_summary,
        "parameters_applied": req.model_dump()
    }



@router.get("/diagnostic", summary="Get diagnostic endpoints for external browser access")
async def get_diagnostic_info() -> Dict[str, Any]:
    return {
        "esp32_cam_url": provider_manager.camera_url,
        "esp32_cam_web_ui": provider_manager.camera_url,
        "esp32_cam_capture_endpoint": f"{provider_manager.camera_url}/capture",
        "esp32_cam_status_endpoint": f"{provider_manager.camera_url}/status",
        "note": "Open esp32_cam_web_ui directly in a new browser tab for raw hardware diagnostic inspection."
    }
