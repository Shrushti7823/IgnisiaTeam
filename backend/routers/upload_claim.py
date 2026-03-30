"""
ClaimIQ - Upload Claim Router (Combined Endpoint)
===================================================
POST /api/upload-claim - Combined endpoint that accepts claim details + file
in one request. Creates claim, saves file, runs OCR, auto-detects document type,
and kicks off the pipeline.
"""
import os
import uuid
import random
import string
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.core.database import get_db, get_new_session
from backend.core.security import get_current_user
from backend.core.config import settings
from backend.models.claim import Claim
from backend.models.document import Document
from backend.models.user import User
from backend.services.ocr_service import process_document
from backend.services.pipeline_service import run_pipeline_sync

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png",
    "image/jpg", "image/tiff", "image/bmp",
}


def _generate_reference() -> str:
    suffix = ''.join(random.choices(string.digits, k=5))
    return f"CLM-{datetime.utcnow().year}-{suffix}"


def _run_pipeline_bg(claim_id: int):
    """Background task: runs full pipeline using its own DB session."""
    db = get_new_session()
    try:
        run_pipeline_sync(claim_id, db)
    except Exception as e:
        print(f"[Pipeline] Error processing claim {claim_id}: {e}")
    finally:
        db.close()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_claim(
    background_tasks: BackgroundTasks,
    claim_type: str = Form(..., description="auto | health | travel | property"),
    incident_date: str = Form(..., description="YYYY-MM-DD"),
    incident_description: str = Form(..., description="Description of the incident"),
    claim_amount: float = Form(..., gt=0, description="Claim amount in dollars"),
    doc_type: str = Form("other", description="Document type: police_report | medical_bill | invoice | photos | id_proof"),
    file: Optional[UploadFile] = File(None, description="PDF or image file (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Combined endpoint: submit a claim + upload a document in one request.
    Creates the claim, saves the file, runs OCR, auto-detects document type,
    and kicks off the processing pipeline.
    """
    # Create claim
    claim = Claim(
        claim_reference=_generate_reference(),
        user_id=current_user.id,
        policy_number=current_user.policy_number,
        claim_type=claim_type,
        incident_date=incident_date,
        incident_description=incident_description,
        claim_amount=claim_amount,
        status="submitted",
        current_stage="submitted",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    document_info = None

    # Process file if uploaded
    if file and file.filename:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            # Still create the claim, just skip the file
            document_info = {"error": f"File type not allowed: {file.content_type}"}
        else:
            content = await file.read()
            size_kb = len(content) / 1024

            if size_kb > settings.MAX_FILE_SIZE_MB * 1024:
                document_info = {"error": f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB"}
            else:
                # Save file
                ext = os.path.splitext(file.filename)[1]
                safe_name = f"{uuid.uuid4().hex}{ext}"
                save_path = os.path.join(settings.UPLOAD_DIR, str(claim.id), safe_name)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                with open(save_path, "wb") as f:
                    f.write(content)

                # Run OCR
                ocr_result = process_document(save_path, doc_type)

                # Save document to DB
                doc = Document(
                    claim_id=claim.id,
                    doc_type=doc_type,
                    file_name=file.filename,
                    file_path=save_path,
                    file_size_kb=round(size_kb, 2),
                    mime_type=file.content_type,
                    ocr_text=ocr_result["ocr_text"],
                    ocr_fields=ocr_result["ocr_fields"],
                    ocr_confidence=ocr_result["ocr_confidence"],
                    tamper_detected=ocr_result["tamper_detected"],
                    detected_doc_type=ocr_result.get("detected_doc_type"),
                    is_verified=not ocr_result["tamper_detected"] and ocr_result["ocr_confidence"] > 0.5,
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)

                document_info = {
                    "document_id": doc.id,
                    "file_name": file.filename,
                    "doc_type": doc_type,
                    "detected_doc_type": ocr_result.get("detected_doc_type"),
                    "ocr_confidence": ocr_result["ocr_confidence"],
                    "extracted_fields": ocr_result["ocr_fields"],
                    "tamper_detected": ocr_result["tamper_detected"],
                    "is_verified": doc.is_verified,
                }

    # Kick off pipeline
    background_tasks.add_task(_run_pipeline_bg, claim.id)

    return {
        "message": "Claim submitted and processing started",
        "claim": {
            "id": claim.id,
            "claim_reference": claim.claim_reference,
            "claim_type": claim.claim_type,
            "claim_amount": claim.claim_amount,
            "status": claim.status,
            "current_stage": claim.current_stage,
        },
        "document": document_info,
        "pipeline": "Processing started in background — poll /api/pipeline/{claim_id}/status for updates",
    }
