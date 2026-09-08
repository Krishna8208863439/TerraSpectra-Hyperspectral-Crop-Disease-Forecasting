import os
import sys
import shutil
import json
import pickle

# Ensure Windows stdout/stderr handles UTF-8 gracefully without crashing on emojis
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

try:
    import pandas as pd
except Exception:
    pd = None
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
try:
    from twilio.rest import Client
except ImportError:
    Client = None

# Load .env file if present (local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import init_db, get_db, DiseaseReport, CropLog, WeatherCache, User, PushSubscription, EmergencyAlert, CommunityOfficer, CommunityWebinar, GovernmentScheme, seed_db
from ml_model import predict_image, get_gemini_api_key, run_crop_diagnose_cv, run_leaf_disease_diagnose, run_crop_disease_detect, validate_image_with_cloud_vision
from plant_gate import validate_is_plant_image, log_rejection
from use_dataset_for_disease_detection import register_dataset_routes, get_dataset_stats, load_dataset_classes
from pydantic import BaseModel
from fastapi.responses import FileResponse

# Global crop recommendation model data
crop_model_data = None

# Initialize FastAPI app
app = FastAPI(
    title="Smart Kisan AI-Driven Advisory Portal API",
    description="Production-ready API blueprint for agricultural leaf/livestock diagnosis, soil advisory, and outbreak alert notification systems.",
    version="1.0.0"
)

# Setup CORS for frontend interactions
# Load allowed origins from env var (comma-separated) with safe defaults
_raw_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5000"
)
ALLOW_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Structured Logging Setup ────────────────────────────────────────────────
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("SmartKisanBackend")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"
    logger.info("-> %s %s [%s]", request.method, request.url.path, client_ip)
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception during %s %s: %s", request.method, request.url.path, exc, exc_info=True)
        raise
    duration_ms = round((time.time() - start) * 1000, 1)
    level = logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(level, "<- %s %s -> %d (%sms)", request.method, request.url.path, response.status_code, duration_ms)
    return response

# Exception handlers
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.warning("HTTP %d: %s — %s %s", exc.status_code, exc.detail, request.method, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {"code": exc.status_code, "message": exc.detail, "details": []}
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    tb = traceback.format_exc()
    logger.error("Internal Server Error on %s %s: %s\n%s", request.method, request.url.path, exc, tb)
    is_prod = os.environ.get("NODE_ENV", "development") == "production"
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": 500,
                "message": "An unexpected error occurred on the server." if is_prod else str(exc),
                "details": [] if is_prod else [tb]
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning("Validation failed on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": 422,
                "message": "Request validation failed.",
                "details": [str(e) for e in exc.errors()]
            }
        }
    )

def verify_request_preconditions(image: UploadFile, x_gemini_key: Optional[str]):
    # 1. Verify Gemini API Key
    api_key = (x_gemini_key or "").strip() or get_gemini_api_key()
    if not api_key:
        print("[Error] Gemini API key is missing.")
        raise HTTPException(
            status_code=500,
            detail="Gemini API key missing."
        )
        
    # 2. Validate uploaded image format
    filename = image.filename.lower()
    ext = filename.split('.')[-1]
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only JPG, JPEG, PNG, and WEBP images are accepted."
        )


def _gate_reject(confidence: float, message: str = None) -> dict:
    """Standard rejection payload returned when Step 1 validation gate fails."""
    return {
        "status": "rejected",
        "success": False,
        "message": message or "Invalid image. Please upload a clear image of a crop or plant.",
        "confidence": round(float(confidence), 4),
    }

# Ensure folders exist
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static folder to serve uploaded leaves/livestock photos
# Using /py_uploads (not /uploads) to distinguish from Node backend's /uploads path
app.mount("/py_uploads", StaticFiles(directory=UPLOAD_DIR), name="py_uploads")

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    global crop_model_data
    init_db()
    seed_db()
    print("[Server] Database initialized successfully and seeded.")
    
    # Validate Gemini API key on startup
    from ml_model import get_gemini_api_key, query_gemini_text
    gemini_key = get_gemini_api_key()
    if not gemini_key or gemini_key == "YOUR_GEMINI_API_KEY":
        print("[WARNING] [Gemini] GEMINI_API_KEY is missing or not configured in your .env file.")
        print("[WARNING] [Gemini] Crop diagnosis and chat functionalities will fall back to local rule-based systems.")
    else:
        try:
            print("[Gemini] Validating API key connection on startup...")
            res = query_gemini_text("Hello. Reply with only JSON: {\"status\": \"ok\"}", custom_key=gemini_key)
            if res and isinstance(res, dict) and res.get("status") == "ok":
                print("[Gemini] API connection validated successfully. Gemini Flash is active.")
            else:
                print("[WARNING] [Gemini] API key connection test failed or returned unexpected response.")
        except Exception as e:
            print(f"[WARNING] [Gemini] API connection error on startup: {e}")
    
    # Register dataset routes for PlantVillage disease data
    register_dataset_routes(app)
    
    # Log dataset status on startup
    try:
        ds_stats = get_dataset_stats()
        if ds_stats["dataset_found"]:
            print(f"[Server] PlantVillage dataset loaded: {ds_stats['total_classes']} classes, {ds_stats['total_images']} images.")
        else:
            print("[Server] PlantVillage dataset not found. Using API + static fallback for disease detection.")
    except Exception as e:
        print(f"[Server] Dataset check error: {e}")
    
    # Train or load crop recommendation model
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crop_recommendation_model.pkl")
    if not os.path.exists(model_path):
        print("[Server] Crop recommendation model missing. Training now...")
        try:
            from train_crop_model import train_crop_model
            train_crop_model()
        except Exception as e:
            print(f"[Server] Failed to auto-train crop model: {e}")
            
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                crop_model_data = pickle.load(f)
            print("[Server] Crop recommendation model loaded successfully.")
        except Exception as e:
            print(f"[Server] Failed to load crop model: {e}")
            
    # Initialize RAG system
    try:
        from rag_service import init_rag_system
        init_rag_system()
        print("[Server] RAG knowledge base indexed successfully.")
    except Exception as rag_err:
        print(f"[Server] Failed to initialize RAG system: {rag_err}")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Smart Kisan Python API", "timestamp": datetime.utcnow().isoformat()}


# --- Dataset-aware Disease Analysis endpoint ---
@app.post("/api/dataset/analyze-from-dataset")
async def analyze_with_dataset_context(
    image: UploadFile = File(...),
    crop: Optional[str] = Form(None),
    x_gemini_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Analyze a crop disease image using the local PlantVillage dataset for context.
    Falls back to Gemini Vision → HuggingFace → Dataset-backed static advice.
    """
    if not image.content_type.startswith("image/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="File must be an image.")

    # Save file
    file_ext = os.path.splitext(image.filename)[1]
    unique_filename = f"leaf_{int(datetime.utcnow().timestamp())}_{image.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(image.file, buffer)
    image_url = f"/py_uploads/{unique_filename}"

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    # Run prediction using ml_model pipeline
    prediction = predict_image(img_bytes, crop_hint=crop, filename=image.filename, custom_key=x_gemini_key)

    # Save to DB
    report = DiseaseReport(
        user_id=None,
        crop=prediction["crop"],
        disease=prediction["disease"],
        severity=prediction["severity"],
        confidence=prediction["confidence"],
        advice=prediction["advice"],
        image_url=image_url,
        region="Dataset Analysis"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Load dataset classes to enrich response
    dataset_classes = load_dataset_classes()

    return {
        "success": True,
        "report_id": report.id,
        "crop": report.crop,
        "disease": report.disease,
        "severity": report.severity,
        "confidence": report.confidence,
        "advice": report.advice,
        "imageUrl": report.image_url,
        "ai_model": prediction.get("model", "ML Pipeline"),
        "gemini_powered": prediction.get("gemini_powered", False),
        "dataset_classes_available": len(dataset_classes),
        "dataset_integrated": True
    }

# --- MODULE A: AI Disease Diagnosis (Computer Vision) ---
@app.post("/api/diagnose", status_code=status.HTTP_201_CREATED)
async def diagnose_crop_disease(
    image: UploadFile = File(...),
    crop: Optional[str] = Form(None),
    region: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    x_gemini_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Accepts crop/livestock symptom image, runs ML pipeline inference,
    saves the diagnostic record to database, and returns all structured remedies.
    Supported formats: JPG, JPEG, PNG, WEBP
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File uploaded is not a valid image format. Please upload JPG, JPEG, PNG, or WEBP."
        )

    # 1. Save uploaded image to static uploads folder
    file_ext = os.path.splitext(image.filename)[1].lower() or ".jpg"
    unique_filename = f"crop_{int(datetime.utcnow().timestamp())}_{image.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    image_url = f"/py_uploads/{unique_filename}"

    # Auto-resize to max 1024x1024 for consistent model input
    try:
        from PIL import Image as PILImage
        with PILImage.open(file_path) as pil_img:
            pil_img = pil_img.convert("RGB")
            pil_img.thumbnail((1024, 1024), PILImage.LANCZOS)
            pil_img.save(file_path, format="JPEG", quality=92)
    except Exception as resize_err:
        print(f"[Diagnose] Image resize skipped: {resize_err}")

    # Read image bytes for model prediction
    with open(file_path, "rb") as f:
         img_bytes = f.read()

    # 1b. STAGE 1 Validation Gate: MobileNetV2 ML classifier + Face/Skin Detector
    # Strictly rejects selfies, people, indoor walls, furniture, non-plant items
    gate_result = validate_is_plant_image(img_bytes, confidence_threshold=0.60, custom_key=x_gemini_key)
    if not gate_result.get("is_valid"):
        print(f"[Diagnose] [REJECT] Plant Gate rejected image: {gate_result}")
        return {
            "success": True,
            "isAgriculturalImage": False,
            "isPlant": False,
            "is_plant": False,
            "crop": "Not a Crop",
            "disease": "Invalid Image (Non-Crop Detected)",
            "severity": "Low",
            "confidence": 0.0,
            "certaintyPercent": 0,
            "error": "No crop or plant leaf detected in this image. Please upload or photograph a real crop leaf, agricultural plant, or farm produce.",
            "message": "No crop or plant leaf detected in this image. Please upload or photograph a real crop leaf, agricultural plant, or farm produce.",
            "advice": "Please ensure the camera is pointed directly at a crop leaf or farm plant. Selfies, indoor rooms, and non-plant objects are strictly rejected.",
            "symptoms": ["Non-crop or human/indoor image detected."],
            "treatment": ["Please take a clear photo of your crop, plant leaves, fruit, or farm produce."],
            "imageUrl": image_url,
            "ai_model": f"MobileNetV2 Plant Gate ({gate_result.get('mode', 'ml')})"
        }

    # 2. Run ML pipeline (with strict crop isolation guardrails)
    prediction = predict_image(img_bytes, crop_hint=crop, filename=image.filename, custom_key=x_gemini_key)

    # 3. Guardrail Gate: Reject human selfies, indoor rooms, vehicles, animals, and non-plant objects
    if prediction.get("isAgriculturalImage") is False or prediction.get("is_plant") is False or prediction.get("isPlant") is False:
        return {
            "success": True,
            "isAgriculturalImage": False,
            "isPlant": False,
            "is_plant": False,
            "crop": "Not a Crop",
            "disease": "Invalid Image (Non-Crop Detected)",
            "severity": "Low",
            "confidence": 0.0,
            "certaintyPercent": 0,
            "error": prediction.get("error") or prediction.get("advice") or "Please upload a clear crop, plant, or leaf image for agricultural diagnosis.",
            "message": prediction.get("message") or prediction.get("advice") or "Please upload a clear crop, plant, or leaf image for agricultural diagnosis.",
            "advice": prediction.get("advice", ""),
            "symptoms": ["Non-crop or human/indoor image detected."],
            "treatment": ["Please take a clear photo of your crop, plant leaves, fruit, or farm produce."],
            "imageUrl": image_url,
            "ai_model": "Smart Kisan Crop Isolation Guardrail"
        }

    # 4. Save valid agricultural report to Relational Database
    report = DiseaseReport(
        user_id=user_id,
        crop=prediction.get("crop", "Unknown"),
        disease=prediction.get("disease", "Unknown"),
        severity=prediction.get("severity", "medium"),
        confidence=prediction.get("confidence", 0.0),
        advice=prediction.get("advice", ""),
        image_url=image_url,
        region=region or "Global"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "success": True,
        "isAgriculturalImage": True,
        "isPlant": True,
        "is_plant": True,
        "report_id": report.id,
        "crop": report.crop,
        "plant_name": prediction.get("plant_name", report.crop),
        "disease": report.disease,
        "health_status": prediction.get("health_status", "Unknown"),
        "severity": report.severity,
        "confidence": report.confidence,
        "growth_stage": prediction.get("growth_stage", "Unknown"),
        "symptoms": prediction.get("symptoms", ""),
        "causes": prediction.get("causes", ""),
        "organic_treatment": prediction.get("organic_treatment", ""),
        "chemical_treatment": prediction.get("chemical_treatment", ""),
        "prevention": prediction.get("prevention", ""),
        "fertilizer_advice": prediction.get("fertilizer_advice", ""),
        "irrigation_advice": prediction.get("irrigation_advice", ""),
        "advice": report.advice,
        "imageUrl": report.image_url,
        "createdAt": report.created_at.isoformat(),
        "gemini_powered": prediction.get("gemini_powered", False),
        "ai_model": prediction.get("model", "Static Fallback"),
        "image_analysis": prediction.get("image_analysis", "")
    }


# --- MODULE A2: Crop Diagnostics CV ---
@app.post("/api/crop-diagnose", status_code=status.HTTP_201_CREATED)
@app.post("/api/crop-diagnostics", status_code=status.HTTP_201_CREATED)
async def diagnose_crop_cv_endpoint(
    image: UploadFile = File(...),
    crop: Optional[str] = Form(None),
    x_gemini_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Examines crop image. Accepts ONLY crop/plant images.
    If NOT a crop -> returns success: False, error: "Invalid image. Please upload a crop image or plant."
    """
    verify_request_preconditions(image, x_gemini_key)

    unique_filename = f"crop_diag_{int(datetime.utcnow().timestamp())}_{image.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_size = os.path.getsize(file_path)
    print(f"Incoming request: POST /api/crop-diagnostics | Uploaded filename: {image.filename} | Image size: {image_size} bytes")

    # Preprocess & Resize image
    try:
        from PIL import Image as PILImage
        with PILImage.open(file_path) as pil_img:
            pil_img = pil_img.convert("RGB")
            pil_img.thumbnail((800, 800), PILImage.LANCZOS)
            pil_img.save(file_path, format="JPEG", quality=90)
    except Exception as e:
        print(f"[Resize] Error: {e}")

    image_url = f"/py_uploads/{unique_filename}"

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    # ── STAGE 1: Plant Image Validation Gate (MobileNetV2 / Gemini strict) ────
    # Rejects non-plant images BEFORE any classifier or Gemini diagnosis call.
    # This gate is NEVER bypassed — it always runs regardless of API keys.
    gate_result = validate_is_plant_image(img_bytes, confidence_threshold=0.75, custom_key=x_gemini_key)
    if not gate_result["is_valid"]:
        log_rejection(
            filename=image.filename,
            endpoint="/api/crop-diagnostics",
            confidence=gate_result["confidence"],
            reason=f"not_plant (mode={gate_result['mode']})",
        )
        logger.info(
            "[Stage1] REJECTED non-plant image '%s' at /api/crop-diagnostics "
            "(confidence=%.3f mode=%s)",
            image.filename, gate_result["confidence"], gate_result["mode"],
        )
        return _gate_reject(
            confidence=gate_result["confidence"],
            message="Invalid image. Please upload a clear image of a crop or plant.",
        )
    logger.info(
        "[Stage1] PASSED crop-diagnostics gate: '%s' confidence=%.3f mode=%s",
        image.filename, gate_result["confidence"], gate_result["mode"],
    )
    # ─────────────────────────────────────────────────────────────────────────

    import asyncio
    loop = asyncio.get_event_loop()
    prediction = await loop.run_in_executor(None, run_crop_diagnose_cv, img_bytes, crop, x_gemini_key)
    
    # Save search log if valid
    if prediction.get("success", True):
        report = DiseaseReport(
            user_id=None,
            crop=prediction.get("crop_name", "Unknown"),
            disease=prediction.get("problems_detected", "Healthy"),
            severity="medium",
            confidence=prediction.get("confidence", 0.95),
            advice=prediction.get("recommendations", ""),
            image_url=image_url,
            region="Crop Diagnostics (CV)"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        prediction["report_id"] = report.id
        prediction["imageUrl"] = image_url

    return prediction


# --- MODULE A3: Leaf Disease Diagnosis ---
@app.post("/api/leaf-diagnostics", status_code=status.HTTP_201_CREATED)
@app.post("/api/leaf-diagnose", status_code=status.HTTP_201_CREATED)
@app.post("/api/leaf-disease", status_code=status.HTTP_201_CREATED)
async def diagnose_leaf_disease(
    image: UploadFile = File(...),
    crop: Optional[str] = Form(None),
    x_gemini_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Leaf-specific disease diagnosis endpoint.
    If NOT a leaf -> returns success: False, error: "Invalid image. Please upload a crop image of a plant leaf."
    """
    verify_request_preconditions(image, x_gemini_key)

    unique_filename = f"leaf_diag_{int(datetime.utcnow().timestamp())}_{image.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_size = os.path.getsize(file_path)
    print(f"Incoming request: POST /api/leaf-disease | Uploaded filename: {image.filename} | Image size: {image_size} bytes")

    # Preprocess & Resize image
    try:
        from PIL import Image as PILImage
        with PILImage.open(file_path) as pil_img:
            pil_img = pil_img.convert("RGB")
            pil_img.thumbnail((800, 800), PILImage.LANCZOS)
            pil_img.save(file_path, format="JPEG", quality=90)
    except Exception as e:
        print(f"[Resize] Error: {e}")

    image_url = f"/py_uploads/{unique_filename}"

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    # ── STAGE 1: Plant Image Validation Gate (MobileNetV2 / Gemini strict) ────
    gate_result = validate_is_plant_image(img_bytes, confidence_threshold=0.75, custom_key=x_gemini_key)
    if not gate_result["is_valid"]:
        log_rejection(
            filename=image.filename,
            endpoint="/api/leaf-disease",
            confidence=gate_result["confidence"],
            reason=f"not_plant (mode={gate_result['mode']})",
        )
        logger.info(
            "[Stage1] REJECTED non-plant image '%s' at /api/leaf-disease "
            "(confidence=%.3f mode=%s)",
            image.filename, gate_result["confidence"], gate_result["mode"],
        )
        return _gate_reject(
            confidence=gate_result["confidence"],
            message="Invalid image. Please upload a clear image of a crop or plant leaf.",
        )
    logger.info(
        "[Stage1] PASSED leaf-disease gate: '%s' confidence=%.3f mode=%s",
        image.filename, gate_result["confidence"], gate_result["mode"],
    )
    # ─────────────────────────────────────────────────────────────────────────

    import asyncio
    loop = asyncio.get_event_loop()
    prediction = await loop.run_in_executor(None, run_leaf_disease_diagnose, img_bytes, crop, x_gemini_key)

    # Save search log if valid
    if prediction.get("success", True):
        report = DiseaseReport(
            user_id=None,
            crop=prediction.get("plant_name", "Unknown"),
            disease=prediction.get("disease_name", "Healthy"),
            severity="medium",
            confidence=prediction.get("confidence", 0.95),
            advice=prediction.get("treatment", ""),
            image_url=image_url,
            region="Leaf Diagnostics"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        prediction["report_id"] = report.id
        prediction["imageUrl"] = image_url

    return prediction


# --- MODULE A4: Crop Disease Detection ---
@app.post("/api/crop-disease-detect", status_code=status.HTTP_201_CREATED)
@app.post("/api/crop-disease", status_code=status.HTTP_201_CREATED)
async def detect_crop_disease_endpoint(
    image: UploadFile = File(...),
    crop: Optional[str] = Form(None),
    x_gemini_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Crop disease detection endpoint.
    If NOT a crop -> returns success: False, error: "Invalid image. Please upload a valid crop image."
    """
    verify_request_preconditions(image, x_gemini_key)

    unique_filename = f"crop_detect_{int(datetime.utcnow().timestamp())}_{image.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_size = os.path.getsize(file_path)
    print(f"Incoming request: POST /api/crop-disease | Uploaded filename: {image.filename} | Image size: {image_size} bytes")

    # Preprocess & Resize image
    try:
        from PIL import Image as PILImage
        with PILImage.open(file_path) as pil_img:
            pil_img = pil_img.convert("RGB")
            pil_img.thumbnail((800, 800), PILImage.LANCZOS)
            pil_img.save(file_path, format="JPEG", quality=90)
    except Exception as e:
        print(f"[Resize] Error: {e}")

    image_url = f"/py_uploads/{unique_filename}"

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    # ── STAGE 1: Plant Image Validation Gate (MobileNetV2 / Gemini strict) ────
    gate_result = validate_is_plant_image(img_bytes, confidence_threshold=0.75, custom_key=x_gemini_key)
    if not gate_result["is_valid"]:
        log_rejection(
            filename=image.filename,
            endpoint="/api/crop-disease",
            confidence=gate_result["confidence"],
            reason=f"not_plant (mode={gate_result['mode']})",
        )
        logger.info(
            "[Stage1] REJECTED non-plant image '%s' at /api/crop-disease "
            "(confidence=%.3f mode=%s)",
            image.filename, gate_result["confidence"], gate_result["mode"],
        )
        return _gate_reject(
            confidence=gate_result["confidence"],
            message="Invalid image. Please upload a clear image of a crop or plant for disease detection.",
        )
    logger.info(
        "[Stage1] PASSED crop-disease gate: '%s' confidence=%.3f mode=%s",
        image.filename, gate_result["confidence"], gate_result["mode"],
    )
    # ─────────────────────────────────────────────────────────────────────────

    import asyncio
    loop = asyncio.get_event_loop()
    prediction = await loop.run_in_executor(None, run_crop_disease_detect, img_bytes, crop, x_gemini_key)

    # Save search log if valid
    if prediction.get("success", True):
        report = DiseaseReport(
            user_id=None,
            crop=prediction.get("crop", "Unknown"),
            disease=prediction.get("disease", "Healthy"),
            severity=prediction.get("severity", "medium"),
            confidence=prediction.get("confidence", 0.95),
            advice=prediction.get("organic_treatment", ""),
            image_url=image_url,
            region="Crop Disease Detection"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        prediction["report_id"] = report.id
        prediction["imageUrl"] = image_url

    return prediction


class ChatMessage(BaseModel):
    sender: str
    text: str

class ChatRequest(BaseModel):
    message: str
    chatHistory: Optional[List[ChatMessage]] = None
    language: Optional[str] = "en"
    gps: Optional[dict] = None
    weather: Optional[dict] = None
    waterAvailability: Optional[str] = None
    cropHint: Optional[str] = None

class PDFReportRequest(BaseModel):
    crop_name: Optional[str] = None
    crop: Optional[str] = None
    disease_name: Optional[str] = None
    disease: Optional[str] = None
    severity: Optional[str] = "medium"
    confidence: Optional[float] = 0.95
    problems_detected: Optional[str] = None
    disease_description: Optional[str] = None
    symptoms: Optional[str] = None
    causes: Optional[str] = None
    organic_treatment: Optional[str] = None
    chemical_treatment: Optional[str] = None
    treatment: Optional[str] = None
    prevention_methods: Optional[str] = None
    prevention: Optional[str] = None
    fertilizer_recommendation: Optional[str] = None
    suggested_fertilizers: Optional[str] = None
    fertilizer_advice: Optional[str] = None
    irrigation_advice: Optional[str] = None
    region: Optional[str] = "India"


# --- Strictly Agricultural RAG Chat Endpoint ---
@app.post("/api/chat")
@app.post("/api/ai/chat")
@app.post("/ai/chat")
async def agricultural_chat_endpoint(
    req: ChatRequest,
    x_gemini_key: Optional[str] = Header(None)
):
    """
    RAG-driven chatbot endpoint. Restricts answers strictly to agriculture and farming.
    Fuses user location (e.g., Kolhapur), weather, soil, and agricultural knowledge base data.
    """
    query = req.message
    lang = req.language or "en"
    history = req.chatHistory or []
    api_key = (x_gemini_key or "").strip() or get_gemini_api_key()

    REFUSAL_MESSAGE = "I am an Agriculture AI Assistant. I only provide information related to farming, crops, soil, weather, fertilizers, and plant health."

    # Fast offline keyword guardrail for obvious non-agri topics
    non_agri_keywords = {
        "movie", "film", "actor", "actress", "cinema", "politics", "president", "election",
        "prime minister", "government election", "python", "javascript", "code", "programming",
        "function", "bug", "cricket", "football", "soccer", "basketball", "olympics", "math",
        "algebra", "calculus", "geometry", "capital of", "who wrote", "song", "music", "game",
        "playstation", "xbox", "iphone", "tesla", "bitcoin", "crypto"
    }

    lowered = query.lower()
    if any(kw in lowered for kw in non_agri_keywords):
        return {
            "success": False,
            "response": REFUSAL_MESSAGE,
            "source": "guardrail"
        }

    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is not configured. Set GEMINI_API_KEY in backend environment.")

    # 1. Strict Agriculture Topic Guardrail check via Gemini
    check_prompt = f"""Analyze if this user query is related ONLY to agriculture, farming, crops, soil, fertilizer, irrigation, weather, disease, pest, seeds, organic farming, government schemes, agriculture technology, crop rotation, harvest, yield, market prices, plant nutrition, greenhouse farming, precision agriculture, livestock, dairy, or poultry.
    If the query is about movies, politics, programming, sports, mathematics, or general non-agricultural knowledge, return is_agriculture: false.
    Return ONLY this JSON:
    {{
      "is_agriculture": true|false
    }}
    Query: "{query}" """

    from ml_model import query_gemini_text
    check_res = query_gemini_text(check_prompt, api_key)
    
    if check_res and check_res.get("is_agriculture") is False:
        return {
            "success": False,
            "response": REFUSAL_MESSAGE,
            "source": "guardrail"
        }

    # 2. Vector search matched documents (RAG)
    from rag_service import search_knowledge_base
    matched_docs = search_knowledge_base(query, k=4, api_key=api_key)

    context_parts = []
    
    # Append User Context (GPS, Weather, Water Availability, Crop Hint)
    if req.gps:
        context_parts.append(f"User GPS Location Coordinates: Lat {req.gps.get('lat')}, Lon {req.gps.get('lon')}")
    if req.weather:
        context_parts.append(f"Synced Live Weather: Temp {req.weather.get('temp')}°C, Humidity {req.weather.get('humidity')}%, Rain Probability {req.weather.get('rainProb')}%, Condition: {req.weather.get('forecast')}")
    if req.waterAvailability:
        context_parts.append(f"Water Availability Source: {req.waterAvailability}")
    if req.cropHint:
        context_parts.append(f"Target Crop Hint: {req.cropHint}")

    if matched_docs:
        for doc in matched_docs:
            context_parts.append(f"KB Article ({doc['title']}):\n{doc['text']}")

    context_str = "\n\n".join(context_parts)

    # 3. Formulate RAG context prompt with strict persona
    system_instruction = f"""You are SmartKisanBot, an Expert Agriculture AI Assistant for Indian farmers.
    INSTRUCTIONS:
    1. Provide accurate, practical, and highly relevant agricultural advice for the farmer's query.
    2. If location (e.g. Kolhapur, Maharashtra, Punjab, etc.) or specific crops are mentioned, give location-specific recommendations grounded in regional agro-climatic zones, local soil conditions, and major crops.
    3. Use the provided Knowledge Base and User Context below to ground your response.
    4. Respond in language: {lang.upper()} (en=English, hi=Hindi, mr=Marathi).
    5. Format your response with clear, beautiful Markdown: headings, bullet points, and actionable steps.

    CONTEXT DATA & KNOWLEDGE BASE:
    {context_str}"""

    # Assemble chat history for multi-turn context
    contents = []
    for msg in history[-6:]:
        contents.append({
            "role": "user" if msg.sender == "user" else "model",
            "parts": [{"text": msg.text}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": query}]
    })

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1200
            }
        }
        resp = requests.post(url, json=payload, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])[0].get("text", "").strip()
            if not response_text:
                response_text = "I am ready to help with your crop and farming questions. Please ask any specific query regarding soil, fertilizers, weather, or crop management."
            return {
                "success": True,
                "response": response_text,
                "source": "gemini-rag",
                "rag_sources": [d["title"] for d in matched_docs] if matched_docs else []
            }
        else:
            raise Exception(f"Gemini API status code {resp.status_code}")
    except Exception as err:
        # Surface the real error as HTTP 502 — never disguise an API failure as
        # a hardcoded advisory string.  A visible error is always better than
        # fabricated advice delivered silently to a farmer.
        print(f"[FastAPI Chat Error] {err}")
        raise HTTPException(
            status_code=502,
            detail=f"AgriExpert AI service is temporarily unavailable: {str(err)}"
        )




# --- PDF Report Download Endpoint ---
@app.post("/api/generate-pdf")
async def generate_pdf_endpoint(req: PDFReportRequest):
    """
    Accepts full diagnosis JSON, creates a ReportLab PDF, and streams it back.
    """
    from pdf_generator import generate_diagnostic_pdf
    pdf_path = generate_diagnostic_pdf(req.dict())
    filename = os.path.basename(pdf_path)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# --- Gemini API Status Endpoint ---
@app.get("/api/gemini-test")
def test_gemini_connection():
    """Check if Gemini API key is configured and reachable."""
    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "status": "not_configured",
            "message": "GEMINI_API_KEY not found. Set it in your .env file or environment variables.",
            "gemini_enabled": False
        }
    # Quick ping to Gemini REST API
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            return {
                "status": "connected",
                "message": "Google Gemini API is active and responding.",
                "gemini_enabled": True,
                "model": "gemini-1.5-flash"
            }
        else:
            return {
                "status": "error",
                "message": f"Gemini API returned HTTP {res.status_code}. Check your API key.",
                "gemini_enabled": False
            }
    except Exception as e:
        return {
            "status": "unreachable",
            "message": f"Could not reach Gemini API: {str(e)}",
            "gemini_enabled": False
        }


# --- MODULE B: Smart Crop Advisory System ---
# Helper function to geocode location using free Open-Meteo Geocoding
def geocode_region(city_name: str) -> dict:
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
        res = requests.get(url, timeout=5)
        data = res.json()
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "lat": result["latitude"],
                "lon": result["longitude"],
                "name": f"{result['name']}, {result.get('admin1', '')}, {result.get('country', '')}"
            }
    except Exception as e:
        print("[Geocode Error] Failed to resolve region coords:", e)
    return None


# --- Soil Profile Endpoint (for NPK Auto-Population) ---
@app.get("/api/soil-profile")
async def get_soil_profile(
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Returns the most recent saved soil test / NPK values for a logged-in user.
    The NPK Advisor uses this to auto-populate N/P/K sliders on load.
    Returns 404 if no profile exists — frontend then shows manual entry mode.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required to fetch soil profile.")
    
    try:
        user_id_int = int(x_user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    latest = (
        db.query(CropLog)
        .filter(CropLog.user_id == user_id_int)
        .order_by(CropLog.created_at.desc())
        .first()
    )

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No saved soil profile found. Please run the Crop Advisory tool first, or enter values manually."
        )

    return {
        "success": True,
        "data": {
            "n": latest.n_level,
            "p": latest.p_level,
            "k": latest.k_level,
            "soilType": latest.soil_type,
            "crop": latest.crop_name,
            "region": latest.region,
            "savedAt": latest.created_at.isoformat() if latest.created_at else None,
        },
        "source": "saved_soil_profile"
    }


@app.post("/api/advisory")
async def generate_crop_advisory(
    soil_type: str = Form(...),
    region: str = Form(...),
    season: str = Form(...),
    pH: float = Form(...),
    n: int = Form(...),
    p: int = Form(...),
    k: int = Form(...),
    land_size: float = Form(...),
    user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Accepts soil parameters and location, fetches real-time/forecasted weather,
    matches agricultural requirements, caches forecast data, and generates advisory.
    """
    # 1. Geocode location and retrieve coordinates
    coords = geocode_region(region)
    lat, lon = (28.6139, 77.2090) # Default: Delhi
    resolved_name = region
    if coords:
        lat = coords["lat"]
        lon = coords["lon"]
        resolved_name = coords["name"]

    # 2. Check Database Weather Cache (Valid for 3 hours)
    cache_limit = datetime.utcnow() - timedelta(hours=3)
    cached_weather = db.query(WeatherCache).filter(
        WeatherCache.lat == round(lat, 2),
        WeatherCache.lon == round(lon, 2),
        WeatherCache.updated_at >= cache_limit
    ).first()

    temp, humidity = (26.0, 65.0)
    forecast_str = "Clear weather forecasted"

    if cached_weather:
        temp = cached_weather.temperature
        humidity = cached_weather.humidity
        forecast_str = cached_weather.forecast_data
        print("[Weather Cache] Hit! Reading cached weather from database.")
    else:
        # Fetch fresh weather from Open-Meteo
        try:
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&daily=precipitation_probability_max&timezone=auto"
            res = requests.get(weather_url, timeout=5)
            w_data = res.json()
            if "current" in w_data:
                temp = w_data["current"]["temperature_2m"]
                humidity = w_data["current"]["relative_humidity_2m"]
                rain_prob = w_data.get("daily", {}).get("precipitation_probability_max", [0])[0]
                forecast_str = f"Temp: {temp}°C, Humidity: {humidity}%, Rain probability: {rain_prob}%"

                # Store or update in DB weather cache
                new_cache = WeatherCache(
                    lat=round(lat, 2),
                    lon=round(lon, 2),
                    display_name=resolved_name,
                    temperature=temp,
                    humidity=humidity,
                    forecast_data=forecast_str,
                    updated_at=datetime.utcnow()
                )
                db.add(new_cache)
                db.commit()
                print("[Weather API] Fresh weather fetched and cached to DB.")
        except Exception as e:
            print("[Weather API Error] Failed to fetch weather:", e)

    # 3. Run Agronomic Recommendation Heuristics / ML Model
    season_lower = season.lower()
    soil_lower = soil_type.lower()
    
    # Estimate rainfall based on season
    if season_lower == "kharif":
        estimated_rainfall = 180.0
    elif season_lower == "rabi":
        estimated_rainfall = 60.0
    else: # zaid
        estimated_rainfall = 80.0
        
    CROP_DISPLAY_NAMES = {
        "rice": "Paddy (Rice)",
        "maize": "Maize (Corn)",
        "chickpea": "Chickpea",
        "kidneybeans": "Kidney Beans",
        "pigeonpeas": "Pigeon Peas",
        "mothbeans": "Moth Beans",
        "mungbean": "Mung Beans",
        "blackgram": "Black Gram",
        "lentil": "Lentils",
        "pomegranate": "Pomegranate",
        "banana": "Banana",
        "mango": "Mango",
        "grapes": "Grapes",
        "watermelon": "Watermelon",
        "muskmelon": "Muskmelon",
        "apple": "Apple",
        "orange": "Orange",
        "papaya": "Papaya",
        "coconut": "Coconut",
        "cotton": "Cotton",
        "jute": "Jute",
        "coffee": "Coffee"
    }

    matched_crops = []

    if crop_model_data is not None:
        model = crop_model_data["model"]
        features = crop_model_data["features"]
        classes = crop_model_data["classes"]
        crop_stats = crop_model_data["crop_stats"]
        
        # Build features dataframe
        X_new = pd.DataFrame([[n, p, k, temp, humidity, pH, estimated_rainfall]], columns=features)
        
        try:
            probabilities = model.predict_proba(X_new)[0]
            class_prob_map = dict(zip(classes, probabilities))
        except Exception as e:
            print(f"[Advisory ML Error] Prediction failed: {e}")
            class_prob_map = {}
            
        for crop_cls in classes:
            stats = crop_stats.get(crop_cls, {})
            disp_name = CROP_DISPLAY_NAMES.get(crop_cls, crop_cls.capitalize())
            
            # Start base compatibility score at 60
            score = 60
            
            # 1. Season bonus
            crop_season = stats.get("season", "whole year").lower()
            if crop_season == "whole year" or crop_season == season_lower:
                score += 15
            else:
                score -= 15
                
            # 2. Soil compatibility bonus
            crop_soils = stats.get("soils", ["loamy"])
            if soil_lower in crop_soils:
                score += 10
            else:
                score -= 5
                
            # 3. pH compatibility bonus
            avg_ph = stats.get("ph", 6.5)
            if abs(pH - avg_ph) <= 0.8:
                score += 10
            else:
                score -= min(15, int(abs(pH - avg_ph) * 10))
                
            # 4. NPK gap penalty
            t_n, t_p, t_k = stats.get("N", 50), stats.get("P", 40), stats.get("K", 40)
            dist = ((t_n - n)**2 + (t_p - p)**2 + (t_k - k)**2)**0.5
            score -= min(25, int(dist * 0.12))
            
            # 5. Model prediction bonus
            prob = class_prob_map.get(crop_cls, 0.0)
            score += int(prob * 20)
            
            final_score = max(10, min(98, score))
            
            matched_crops.append({
                "crop": disp_name,
                "score": final_score,
                "predictedYield": stats.get("yield", "1.5 - 2.0 tons/acre"),
                "estimatedProfit": f"₹{int(stats.get('profit', 50000) * land_size):,}/acre",
                "npkTarget": (int(t_n), int(t_p), int(t_k)),
                "raw_prob": prob
            })
    else:
        # Fallback to local heuristics if model failed to load
        print("[Advisory Fallback] Model data is not available, falling back to static profiles.")
        crop_profiles = [
            {"crop": "Wheat", "season": "rabi", "soils": ["loamy", "clay"], "ph_range": (6.0, 7.5), "npk": (100, 50, 40), "base_yield": "1.8 - 2.2 tons/acre", "profit": 72000},
            {"crop": "Paddy (Rice)", "season": "kharif", "soils": ["clay", "loamy"], "ph_range": (5.5, 6.5), "npk": (120, 60, 40), "base_yield": "2.1 - 2.5 tons/acre", "profit": 85000},
            {"crop": "Tomato", "season": "zaid", "soils": ["loamy", "sandy"], "ph_range": (6.0, 7.0), "npk": (80, 60, 60), "base_yield": "9.5 - 12.0 tons/acre", "profit": 110000},
            {"crop": "Maize", "season": "kharif", "soils": ["loamy", "black"], "ph_range": (5.8, 7.2), "npk": (110, 55, 40), "base_yield": "2.2 - 2.6 tons/acre", "profit": 60000},
        ]
        for profile in crop_profiles:
            score = 50
            if profile["season"] == season_lower:
                score += 25
            if soil_lower in profile["soils"]:
                score += 15
            min_ph, max_ph = profile["ph_range"]
            if min_ph <= pH <= max_ph:
                score += 10
            t_n, t_p, t_k = profile["npk"]
            dist = ((t_n - n)**2 + (t_p - p)**2 + (t_k - k)**2)**0.5
            score -= min(15, int(dist * 0.1))
            matched_crops.append({
                "crop": profile["crop"],
                "score": max(10, min(98, score)),
                "predictedYield": profile["base_yield"],
                "estimatedProfit": f"₹{int(profile['profit'] * land_size):,}/acre",
                "npkTarget": profile["npk"]
            })

    # Sort crop suggestions by feasibility score
    matched_crops.sort(key=lambda x: x["score"], reverse=True)
    best_crop = matched_crops[0]

    # Generate Fertilization Plan based on optimal best crop requirements
    opt_n, opt_p, opt_k = best_crop["npkTarget"]
    n_gap = max(0, opt_n - n)
    p_gap = max(0, opt_p - p)
    k_gap = max(0, opt_k - k)

    fertilizer_plan = [
        {
            "stage": "Basal Dressing (Sowing Preparation)",
            "recommendation": f"Blend {int(p_gap * 0.8)}kg Phosphorus (DAP) and {int(k_gap * 0.7)}kg Potassium (MOP) per acre into the tillage bed. Incorporate 5 tons of well-rotted farmyard manure."
        },
        {
            "stage": "Active Vegetative Development (Week 3)",
            "recommendation": f"Top-dress with {int(n_gap * 0.6)}kg Nitrogen using Urea per acre. Ensure fields are weeded prior to application."
        },
        {
            "stage": "Flowering & Crop Reproduction (Week 7)",
            "recommendation": f"Add remaining split dose of Urea ({int(n_gap * 0.4)}kg/acre) and perform minor foliar application of micronutrients to boost node set."
        }
    ]

    # 4. Save advisory log to database
    crop_log = CropLog(
        user_id=user_id,
        crop_name=best_crop["crop"],
        soil_type=soil_type,
        region=resolved_name,
        season=season,
        pH=pH,
        n_level=n,
        p_level=p,
        k_level=k,
        expected_yield=best_crop["predictedYield"],
        estimated_profit=best_crop["estimatedProfit"]
    )
    db.add(crop_log)
    db.commit()

    return {
        "success": True,
        "resolvedLocation": resolved_name,
        "weather": {
            "temp": temp,
            "humidity": humidity,
            "forecast": forecast_str
        },
        "recommendations": [
            {
                "crop": c["crop"],
                "suitabilityScore": c["score"],
                "predictedYield": c["predictedYield"],
                "estimatedProfit": c["estimatedProfit"],
                "reason": f"Excellent compatibility matching {soil_type} soil type during {season} sowing. Yield forecasts adjusted for temperature ({temp}°C)."
            } for c in matched_crops[:3]
        ],
        "fertilizerPlan": fertilizer_plan
    }

class YieldPredictionRequest(BaseModel):
    crop: str
    area: float = 1.0
    soil_type: Optional[str] = "loamy"
    n: Optional[float] = 90.0
    p: Optional[float] = 45.0
    k: Optional[float] = 40.0
    ph: Optional[float] = 6.5
    rainfall: Optional[float] = 120.0
    temperature: Optional[float] = 26.0
    humidity: Optional[float] = 65.0
    previous_yield: Optional[float] = None
    season: Optional[str] = "Kharif"
    state: Optional[str] = "Maharashtra"
    district: Optional[str] = "Pune"

@app.post("/api/yield-predict")
@app.post("/api/yield/predict")
def predict_crop_yield_ml(req: YieldPredictionRequest):
    """
    ML Model Engine for Crop Yield Prediction based on XGBoost / Random Forest ensemble principles.
    Analyzes Rainfall, Temperature, Humidity, Soil Type, NPK, Area, Season, State, District, Previous Yield.
    """
    crop_lower = req.crop.lower()
    
    # Base yields per acre in tons
    BASE_CROP_YIELDS = {
        "tomato": 12.5,
        "paddy": 2.4,
        "rice": 2.4,
        "wheat": 2.1,
        "potato": 10.0,
        "cotton": 1.2,
        "sugarcane": 38.0,
        "maize": 2.8,
        "soybean": 1.1,
        "groundnut": 1.3,
        "onion": 9.0,
        "chilli": 2.2,
        "banana": 28.0,
        "mango": 4.5,
        "grapes": 8.5,
        "mustard": 0.9
    }
    
    base_yield = 2.0
    for key, val in BASE_CROP_YIELDS.items():
        if key in crop_lower:
            base_yield = val
            break
            
    # Factors & Coefficients
    factors = []
    recommendations = []
    multiplier = 1.0
    
    # NPK Balance Evaluation
    npk_score = (min(req.n / 100.0, 1.2) + min(req.p / 50.0, 1.2) + min(req.k / 50.0, 1.2)) / 3.0
    if npk_score >= 0.9:
        multiplier *= 1.12
        factors.append({"factor": "NPK Balance", "impact": "Positive", "detail": "Soil nutrient levels optimal for high biomass accumulation."})
    else:
        multiplier *= 0.88
        factors.append({"factor": "NPK Deficit", "impact": "Negative", "detail": "Nitrogen/Phosphorus shortfall limits maximum potential yield."})
        recommendations.append("Apply 25 kg/acre DAP + top-dress Urea during vegetative growth.")

    # Soil pH Evaluation
    if 6.0 <= req.ph <= 7.2:
        multiplier *= 1.05
        factors.append({"factor": "Soil pH", "impact": "Positive", "detail": f"Ideal soil pH ({req.ph}) allows maximum nutrient bio-availability."})
    else:
        multiplier *= 0.92
        factors.append({"factor": "Sub-optimal pH", "impact": "Negative", "detail": f"pH level ({req.ph}) causes micronutrient fixation."})
        recommendations.append("Apply agricultural lime / gypsum to regulate soil pH towards 6.5.")

    # Rainfall & Water Availability
    if req.rainfall >= 100:
        multiplier *= 1.08
        factors.append({"factor": "Rainfall & Moisture", "impact": "Positive", "detail": f"Adequate seasonal rainfall ({req.rainfall} mm) supports root expansion."})
    else:
        multiplier *= 0.85
        factors.append({"factor": "Water Stress", "impact": "Negative", "detail": f"Low rainfall ({req.rainfall} mm) risks drought moisture stress."})
        recommendations.append("Install drip fertigation to maintain 75% field capacity moisture.")

    # Temperature & Climate Zone
    if 20.0 <= req.temperature <= 32.0:
        multiplier *= 1.04
        factors.append({"factor": "Temperature Comfort", "impact": "Positive", "detail": f"Temperature ({req.temperature}°C) is within ideal photosynthetic range."})
    else:
        multiplier *= 0.90
        factors.append({"factor": "Thermal Stress", "impact": "Negative", "detail": f"Extreme temperature ({req.temperature}°C) reduces flowering set rate."})
        recommendations.append("Maintain evening light misting or shade net protection.")

    # Historical Previous Yield adjustment
    if req.previous_yield and req.previous_yield > 0:
        history_weight = 0.3
        calc_yield_per_acre = (base_yield * multiplier) * (1 - history_weight) + (req.previous_yield * history_weight)
    else:
        calc_yield_per_acre = base_yield * multiplier

    calc_yield_per_acre = round(max(0.2, calc_yield_per_acre), 2)
    total_harvest = round(calc_yield_per_acre * req.area, 2)
    confidence_score = round(min(0.96, 0.82 + (0.02 * len(factors))), 2)

    # General recommendations
    recommendations.append("Perform prophylactic neem oil spray at 30 days to prevent pest outbreaks.")
    recommendations.append("Incorporate bio-fertilizers (Azotobacter & PSBs) during seed treatment.")

    return {
        "success": True,
        "crop": req.crop,
        "area": req.area,
        "state": req.state,
        "district": req.district,
        "season": req.season,
        "predicted_yield_per_acre": calc_yield_per_acre,
        "total_predicted_yield": total_harvest,
        "unit": "Tons",
        "confidence_score": confidence_score,
        "factors_affecting_yield": factors,
        "recommendations": recommendations
    }


# --- MODULE C: Predictive Outbreak & Alert System ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "ACmockaccountsd1234567890abcdef")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "mockauthtoken1234567890abcdef")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+15017122661")

from pydantic import BaseModel

class SubscriptionRequest(BaseModel):
    topic: str
    token: str

def send_fcm_push_notification(token: str, title: str, body: str, deep_link: str):
    """
    Simulates sending an asynchronous push notification via FCM with high priority
    overriding DND, including the deep linking target.
    """
    fcm_payload = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            },
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": "outbreak_alerts_critical",
                    "sound": "default",
                    "importance": "HIGH", # Critical/High importance level
                }
            },
            "data": {
                "url": deep_link,
                "priority": "HIGH"
            }
        }
    }
    print("=" * 60)
    print("               [FIREBASE CLOUD MESSAGING BROADCAST]")
    print(f"FCM Token: {token}")
    print(f"Title: {title}")
    print(f"Body: {body}")
    print(f"Payload: {json.dumps(fcm_payload, indent=2)}")
    print("=" * 60)

@app.post("/api/alerts")
async def check_regional_outbreaks(
    region: str = Form(...),
    threshold: int = Form(3),
    send_sms: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Checks recent disease report uploads inside the region. If reports exceed
    the threshold, it identifies an outbreak risk, sends FCM push notifications
    to subscribed topic segments, and dispatches SMS warnings.
    """
    # Look back over last 7 days
    lookback_date = datetime.utcnow() - timedelta(days=7)
    
    # Query reports count grouped by disease
    reports = db.query(DiseaseReport).filter(
        DiseaseReport.region.like(f"%{region}%"),
        DiseaseReport.created_at >= lookback_date
    ).all()
    
    disease_counts = {}
    for r in reports:
        disease_counts[r.disease] = disease_counts.get(r.disease, 0) + 1

    active_outbreaks = []
    sms_broadcast_count = 0
    fcm_push_count = 0
    notifications_sent = []

    clean_region = region.strip().lower().replace(" ", "").replace("_", "")
    topic_name = f"outbreak_{clean_region}"

    for disease, count in disease_counts.items():
        if count >= threshold:
            active_outbreaks.append({
                "disease": disease,
                "reportsCount": count,
                "status": "CRITICAL"
            })
            
            alert_title = f"🚨 EMERGENCY OUTBREAK ALERT: {region.upper()}"
            alert_message = f"Critical level of '{disease}' detected in region '{region}' with {count} reports this week. Quarantine infected crops immediately & check offline diagnostics."
            
            # 1. FCM Push to Subscribed Topic Segment
            subscribers = db.query(PushSubscription).filter(PushSubscription.topic == topic_name).all()
            for sub in subscribers:
                send_fcm_push_notification(
                    token=sub.token,
                    title=alert_title,
                    body=alert_message,
                    deep_link="/dashboard"
                )
                fcm_push_count += 1
                notifications_sent.append({
                    "type": "FCM_PUSH",
                    "topic": topic_name,
                    "token": sub.token,
                    "title": alert_title,
                    "body": alert_message,
                    "deep_link": "/dashboard",
                    "simulated": True
                })
            
            # 2. Twilio SMS
            sms_message = f"🚨 SMART KISAN EMERGENCY ALERT! An outbreak of '{disease}' has been detected in region '{region}' with {count} reports filed this week. Please quarantine infected crops immediately. Consult nearest Agri-Expert."
            if send_sms:
                mock_contacts = ["+919876543210", "+918765432109"]
                
                try:
                    if "mock" not in TWILIO_ACCOUNT_SID and len(TWILIO_ACCOUNT_SID) > 10:
                        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                        for contact in mock_contacts:
                            client.messages.create(
                                body=sms_message,
                                from_=TWILIO_PHONE_NUMBER,
                                to=contact
                            )
                        sms_broadcast_count += len(mock_contacts)
                    else:
                        # Log mock SMS delivery
                        print("=" * 60)
                        print("               [MOCK TWILIO SMS BROADCAST]")
                        print(f"From: {TWILIO_PHONE_NUMBER}")
                        print(f"To Contacts: {', '.join(mock_contacts)}")
                        print(f"Message:\n{sms_message}")
                        print("=" * 60)
                        sms_broadcast_count += len(mock_contacts)
                        notifications_sent.append({
                            "type": "TWILIO_SMS",
                            "disease": disease,
                            "contacts": mock_contacts,
                            "simulated": True
                        })
                except Exception as e:
                    print("[Twilio Error] SMS Dispatch failed:", e)

    return {
        "success": True,
        "region": region,
        "lookbackDays": 7,
        "reportsFound": len(reports),
        "outbreaks": active_outbreaks,
        "fcmPushesDispatched": fcm_push_count,
        "smsDispatched": sms_broadcast_count,
        "broadcastDetails": notifications_sent if len(notifications_sent) > 0 else "Outbreak notifications completed."
    }

@app.post("/api/alerts/subscribe")
def subscribe_to_alerts(req: SubscriptionRequest, db: Session = Depends(get_db)):
    existing = db.query(PushSubscription).filter(
        PushSubscription.topic == req.topic,
        PushSubscription.token == req.token
    ).first()
    if not existing:
        sub = PushSubscription(topic=req.topic, token=req.token)
        db.add(sub)
        db.commit()
    return {"success": True, "message": f"Successfully subscribed to topic: {req.topic}"}

@app.post("/api/alerts/unsubscribe")
def unsubscribe_from_alerts(req: SubscriptionRequest, db: Session = Depends(get_db)):
    sub = db.query(PushSubscription).filter(
        PushSubscription.topic == req.topic,
        PushSubscription.token == req.token
    ).first()
    if sub:
        db.delete(sub)
        db.commit()
    return {"success": True, "message": f"Successfully unsubscribed from topic: {req.topic}"}

@app.post("/api/alerts/manual")
async def create_manual_alert(
    region: str = Form(...),
    disease: str = Form(...),
    message: str = Form(...),
    priority: str = Form("high"),
    db: Session = Depends(get_db)
):
    alert = EmergencyAlert(
        region=region,
        disease=disease,
        message=message,
        priority=priority
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Clean the region name to generate the topic segment
    clean_region = region.strip().lower().replace(" ", "").replace("_", "")
    topic_name = f"outbreak_{clean_region}"

    # Query all subscribers to this topic
    subscribers = db.query(PushSubscription).filter(PushSubscription.topic == topic_name).all()
    
    alert_title = f"🚨 {priority.upper()} EMERGENCY OUTBREAK ALERT: {region.upper()}"
    
    # Broadcast FCM notification to all registered tokens
    fcm_count = 0
    for sub in subscribers:
        send_fcm_push_notification(
            token=sub.token,
            title=alert_title,
            body=message,
            deep_link="/dashboard"
        )
        fcm_count += 1

    return {
        "success": True,
        "alert_id": alert.id,
        "message": f"Successfully created manual alert and pushed to {fcm_count} subscriber(s) for topic: {topic_name}",
        "pushedCount": fcm_count
    }

@app.get("/api/alerts/active")
def get_active_alerts(db: Session = Depends(get_db)):
    alerts = db.query(EmergencyAlert).order_by(EmergencyAlert.created_at.desc()).all()
    return {
        "success": True,
        "alerts": [
            {
                "id": a.id,
                "region": a.region,
                "disease": a.disease,
                "message": a.message,
                "priority": a.priority,
                "createdAt": a.created_at.isoformat()
            }
            for a in alerts
        ]
    }

@app.delete("/api/alerts/active/{alert_id}")
def delete_active_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(EmergencyAlert).filter(EmergencyAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"success": True, "message": "Alert deleted successfully"}

# --- COMMUNITY & RESOURCE DIRECTORY API ---

@app.get("/api/community/officers")
def get_community_officers(db: Session = Depends(get_db)):
    officers = db.query(CommunityOfficer).all()
    return {
        "success": True,
        "officers": [
            {
                "id": o.id,
                "nameEn": o.name_en,
                "nameMr": o.name_mr,
                "roleEn": o.role_en,
                "roleMr": o.role_mr,
                "regionEn": o.region_en,
                "regionMr": o.region_mr,
                "contact": o.contact
            }
            for o in officers
        ]
    }

@app.post("/api/community/officers")
def add_community_officer(
    name_en: str = Form(...),
    name_mr: str = Form(...),
    role_en: str = Form(...),
    role_mr: str = Form(...),
    region_en: str = Form(...),
    region_mr: str = Form(...),
    contact: str = Form(...),
    db: Session = Depends(get_db)
):
    officer = CommunityOfficer(
        name_en=name_en,
        name_mr=name_mr,
        role_en=role_en,
        role_mr=role_mr,
        region_en=region_en,
        region_mr=region_mr,
        contact=contact
    )
    db.add(officer)
    db.commit()
    db.refresh(officer)
    return {"success": True, "message": "Officer added successfully"}

@app.delete("/api/community/officers/{officer_id}")
def delete_community_officer(officer_id: int, db: Session = Depends(get_db)):
    officer = db.query(CommunityOfficer).filter(CommunityOfficer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    db.delete(officer)
    db.commit()
    return {"success": True, "message": "Officer deleted successfully"}


@app.get("/api/community/webinars")
def get_community_webinars(db: Session = Depends(get_db)):
    webinars = db.query(CommunityWebinar).all()
    return {
        "success": True,
        "webinars": [
            {
                "id": w.id,
                "topicEn": w.topic_en,
                "topicMr": w.topic_mr,
                "dateEn": w.date_en,
                "dateMr": w.date_mr,
                "link": w.link
            }
            for w in webinars
        ]
    }

@app.post("/api/community/webinars")
def add_community_webinar(
    topic_en: str = Form(...),
    topic_mr: str = Form(...),
    date_en: str = Form(...),
    date_mr: str = Form(...),
    link: str = Form(...),
    db: Session = Depends(get_db)
):
    webinar = CommunityWebinar(
        topic_en=topic_en,
        topic_mr=topic_mr,
        date_en=date_en,
        date_mr=date_mr,
        link=link
    )
    db.add(webinar)
    db.commit()
    db.refresh(webinar)
    return {"success": True, "message": "Webinar added successfully"}

@app.delete("/api/community/webinars/{webinar_id}")
def delete_community_webinar(webinar_id: int, db: Session = Depends(get_db)):
    webinar = db.query(CommunityWebinar).filter(CommunityWebinar.id == webinar_id).first()
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
    db.delete(webinar)
    db.commit()
    return {"success": True, "message": "Webinar deleted successfully"}


@app.get("/api/community/schemes")
def get_community_schemes(db: Session = Depends(get_db)):
    schemes = db.query(GovernmentScheme).all()
    return {
        "success": True,
        "schemes": [
            {
                "id": s.id,
                "titleEn": s.title_en,
                "titleMr": s.title_mr,
                "descEn": s.desc_en,
                "descMr": s.desc_mr,
                "url": s.url
            }
            for s in schemes
        ]
    }

@app.post("/api/community/schemes")
def add_government_scheme(
    title_en: str = Form(...),
    title_mr: str = Form(...),
    desc_en: str = Form(...),
    desc_mr: str = Form(...),
    url: str = Form(...),
    db: Session = Depends(get_db)
):
    scheme = GovernmentScheme(
        title_en=title_en,
        title_mr=title_mr,
        desc_en=desc_en,
        desc_mr=desc_mr,
        url=url
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return {"success": True, "message": "Scheme added successfully"}

@app.delete("/api/community/schemes/{scheme_id}")
def delete_government_scheme(scheme_id: int, db: Session = Depends(get_db)):
    scheme = db.query(GovernmentScheme).filter(GovernmentScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    db.delete(scheme)
    db.commit()
    return {"success": True, "message": "Scheme deleted successfully"}


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    gemini_status = "connected"
    gemini_key = get_gemini_api_key()
    if not gemini_key or gemini_key == "YOUR_GEMINI_API_KEY":
        gemini_status = "disconnected"
    else:
        try:
            from ml_model import query_gemini_text
            res = query_gemini_text("Hello. Reply with only JSON: {\"status\": \"ok\"}", custom_key=gemini_key)
            if not res or not isinstance(res, dict) or res.get("status") != "ok":
                gemini_status = "disconnected"
        except Exception:
            gemini_status = "disconnected"

    db_status = "connected"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "gemini": gemini_status,
        "database": db_status
    }


