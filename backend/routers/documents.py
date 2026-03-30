"""
ClaimIQ - Documents Router
File upload with automatic OCR processing
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.config import settings
from backend.models.document import Document
from backend.models.claim import Claim
from backend.models.user import User
from backend.services.ocr_service import process_document

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png",
    "image/jpg", "image/tiff", "image/bmp",
}

DOC_TYPE_CHOICES = [
    "police_report", "medical_bill", "invoice",
    "photos", "id_proof", "booking_proof", "other",
]


@router.post("/upload/{claim_id}")
async def upload_document(
    claim_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document for a claim. Runs OCR automatically."""
    # Validate claim belongs to user
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.user_id != current_user.id and current_user.role not in ["admin", "adjuster"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate doc_type
    if doc_type not in DOC_TYPE_CHOICES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Choose from: {DOC_TYPE_CHOICES}")

    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {file.content_type}")

    # Check file size
    content = await file.read()
    size_kb = len(content) / 1024
    if size_kb > settings.MAX_FILE_SIZE_MB * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    # Save file
    ext = os.path.splitext(file.filename)[1]
    safe_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, str(claim_id), safe_name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(content)

    # Run OCR
    ocr_result = process_document(save_path, doc_type)

    # Auto-detect: use AI-detected doc subtype when available
    detected_subtype = ocr_result.get("detected_doc_subtype", "unknown")
    user_selected_type = doc_type
    actual_doc_type = doc_type  # default to user selection

    # Override user selection with AI detection if confident
    if detected_subtype != "unknown" and detected_subtype in DOC_TYPE_CHOICES:
        actual_doc_type = detected_subtype
        if detected_subtype != doc_type:
            print(f"[Documents] Auto-corrected doc type: user={doc_type} → AI={detected_subtype}")

    # Save to DB with the AI-corrected doc type
    doc = Document(
        claim_id=claim_id,
        doc_type=actual_doc_type,
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

    # Run image fraud detection (hashing + signature/stamp)
    image_fraud_info = {}
    try:
        from backend.services.image_fraud_service import run_image_fraud_check

        # Get existing hashes for duplicate check
        all_docs = db.query(Document).filter(
            Document.image_phash.isnot(None),
            Document.claim_id != claim_id,
        ).all()
        existing_hashes = [
            {"claim_id": d.claim_id, "document_id": d.id,
             "phash": d.image_phash, "dhash": d.image_dhash}
            for d in all_docs
        ]

        img_result = run_image_fraud_check(
            file_path=save_path,
            doc_type=doc_type,
            claim_id=claim_id,
            existing_hashes=existing_hashes,
        )
        doc.image_phash = img_result.get("phash")
        doc.image_dhash = img_result.get("dhash")
        doc.has_signature = img_result.get("signature_stamp", {}).get("has_signature")
        doc.has_stamp = img_result.get("signature_stamp", {}).get("has_stamp")

        image_fraud_info = {
            "is_duplicate": img_result.get("is_duplicate", False),
            "duplicates_found": len(img_result.get("duplicates_found", [])),
            "has_signature": doc.has_signature,
            "has_stamp": doc.has_stamp,
            "fraud_signals": img_result.get("fraud_signals", []),
        }
    except Exception as e:
        print(f"[Documents] Image fraud check error: {e}")

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "message": "Document uploaded and processed",
        "document_id": doc.id,
        "doc_type": actual_doc_type,
        "user_selected_type": user_selected_type,
        "detected_doc_subtype": detected_subtype,
        "detected_doc_type": ocr_result.get("detected_doc_type"),
        "auto_classified": actual_doc_type != user_selected_type,
        "file_name": file.filename,
        "ocr_confidence": ocr_result["ocr_confidence"],
        "extracted_fields": ocr_result["ocr_fields"],
        "tamper_detected": ocr_result["tamper_detected"],
        "is_verified": doc.is_verified,
        "image_fraud": image_fraud_info,
    }


@router.get("/claim/{claim_id}")
def get_claim_documents(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for a claim."""
    docs = db.query(Document).filter(Document.claim_id == claim_id).all()
    return [
        {
            "id": d.id,
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "file_size_kb": d.file_size_kb,
            "is_verified": d.is_verified,
            "tamper_detected": d.tamper_detected,
            "ocr_confidence": d.ocr_confidence,
            "ocr_fields": d.ocr_fields,
            "uploaded_at": d.uploaded_at,
        }
        for d in docs
    ]
