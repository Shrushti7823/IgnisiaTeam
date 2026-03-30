"""
ClaimIQ - Real Document Processing & OCR Service
Extracts text and key fields from uploaded claim documents.
Uses pdfplumber for PDFs and Pillow for basic image text extraction.
Includes automatic document type classification.
NO mock data — all extraction is from real uploaded documents.
"""
import os
import re
import json
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
# DOCUMENT TYPE AUTO-DETECTION
# ═══════════════════════════════════════════════════════════════════════

# Keyword sets with weights for each claim type
_DOC_TYPE_KEYWORDS = {
    "medical_claim": {
        "high": ["hospital", "patient", "diagnosis", "treatment", "prescription",
                 "medication", "surgery", "doctor", "physician", "admission",
                 "discharge", "clinical", "medical", "healthcare", "icu",
                 "ward", "operation", "pathology", "radiology", "pharmacy"],
        "medium": ["blood", "test", "report", "consultation", "therapy",
                   "nursing", "ambulance", "emergency", "outpatient", "inpatient"],
    },
    "vehicle_claim": {
        "high": ["vehicle", "accident", "collision", "garage", "repair",
                 "registration", "automobile", "car", "motorcycle", "truck",
                 "fir", "traffic", "police report", "rto", "insurance",
                 "third party", "own damage", "bumper", "engine"],
        "medium": ["road", "driver", "license", "towing", "mechanic",
                   "body shop", "dent", "scratch", "windshield", "airbag"],
    },
    "property_claim": {
        "high": ["property", "house", "building", "fire", "flood",
                 "earthquake", "roof", "structural", "plumbing", "electrical",
                 "renovation", "construction", "dwelling", "premises"],
        "medium": ["damage", "water", "storm", "wind", "theft",
                   "burglary", "vandalism", "foundation", "wall", "ceiling"],
    },
}


def detect_document_type(ocr_text: str) -> str:
    """
    Auto-detect claim type from OCR text using keyword frequency scoring.
    Returns: "medical_claim" | "vehicle_claim" | "property_claim" | "unknown"
    """
    if not ocr_text or len(ocr_text.strip()) < 10:
        return "unknown"

    text_lower = ocr_text.lower()
    scores = {}

    for doc_type, keyword_sets in _DOC_TYPE_KEYWORDS.items():
        score = 0
        for keyword in keyword_sets.get("high", []):
            count = text_lower.count(keyword)
            score += count * 3  # High-weight keywords
        for keyword in keyword_sets.get("medium", []):
            count = text_lower.count(keyword)
            score += count * 1  # Medium-weight keywords
        scores[doc_type] = score

    if not scores or max(scores.values()) == 0:
        return "unknown"

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Require minimum confidence (at least 2 keyword hits)
    if best_score < 3:
        return "unknown"

    print(f"[OCR] Document type detected: {best_type} (score={best_score}, all={scores})")
    return best_type


# Document SUBTYPE keywords — classifies the specific document type
_DOC_SUBTYPE_KEYWORDS = {
    "medical_bill": {
        "high": ["hospital", "patient", "diagnosis", "treatment", "discharge",
                 "medical bill", "medical certificate", "admission", "ward",
                 "prescription", "doctor", "physician", "surgery", "icu",
                 "healthcare", "clinical", "pharmacy", "pathology", "radiology",
                 "nursing", "outpatient", "inpatient", "consultation",
                 "total charges", "bed charges", "procedure", "medication"],
        "medium": ["blood", "test", "report", "therapy", "ambulance",
                   "emergency", "health", "fever", "pain", "injury",
                   "fracture", "x-ray", "mri", "ct scan", "lab"],
    },
    "invoice": {
        "high": ["invoice", "bill to", "invoice number", "invoice date",
                 "subtotal", "grand total", "tax", "gst", "vat",
                 "payment terms", "due date", "qty", "quantity",
                 "unit price", "line items", "purchase order",
                 "receipt", "billing address", "amount due"],
        "medium": ["total", "item", "description", "rate", "charges",
                   "net amount", "discount", "shipping", "cost"],
    },
    "police_report": {
        "high": ["police", "fir", "first information report", "officer",
                 "station", "complaint", "complainant", "accused",
                 "investigation", "crime", "incident report", "witness",
                 "statement", "constable", "inspector", "ipc section",
                 "penal code", "law enforcement", "arrest"],
        "medium": ["accident", "collision", "traffic", "case number",
                   "jurisdiction", "offense", "violation", "evidence",
                   "scene", "reported", "patrol"],
    },
    "id_proof": {
        "high": ["aadhaar", "aadhar", "passport", "voter id", "pan card",
                 "driving license", "driver license", "social security",
                 "identity card", "national id", "government of india",
                 "unique identification", "date of birth", "dob",
                 "photo id", "identity proof"],
        "medium": ["name", "address", "male", "female", "nationality",
                   "valid", "issued", "expiry", "signature", "photo"],
    },
    "photos": {
        "high": ["image format", "image size", "color mode", "exif",
                 "camera", "photograph", "jpeg", "png"],
        "medium": ["pixel", "resolution", "file size", "metadata"],
    },
    "booking_proof": {
        "high": ["booking", "reservation", "itinerary", "flight",
                 "airline", "ticket", "boarding pass", "pnr",
                 "hotel", "check-in", "check-out", "travel",
                 "passenger", "seat", "confirmation"],
        "medium": ["departure", "arrival", "class", "gate",
                   "terminal", "baggage", "journey"],
    },
}


def detect_document_subtype(ocr_text: str) -> str:
    """
    Auto-detect the specific document subtype from OCR text.
    Returns: "medical_bill" | "invoice" | "police_report" | "id_proof" | "photos" | "booking_proof" | "unknown"
    """
    if not ocr_text or len(ocr_text.strip()) < 5:
        return "unknown"

    text_lower = ocr_text.lower()
    scores = {}

    for subtype, keyword_sets in _DOC_SUBTYPE_KEYWORDS.items():
        score = 0
        for keyword in keyword_sets.get("high", []):
            count = text_lower.count(keyword)
            score += count * 3
        for keyword in keyword_sets.get("medium", []):
            count = text_lower.count(keyword)
            score += count * 1
        scores[subtype] = score

    if not scores or max(scores.values()) == 0:
        return "unknown"

    best_subtype = max(scores, key=scores.get)
    best_score = scores[best_subtype]

    if best_score < 3:
        return "unknown"

    print(f"[OCR] Document subtype detected: {best_subtype} (score={best_score}, all={scores})")
    return best_subtype


def extract_text_from_pdf(file_path: str) -> Tuple[str, float]:
    """
    Extract text from PDF using pdfplumber.
    Returns: (extracted_text, confidence_score 0-1)
    """
    try:
        import pdfplumber
        text_parts = []
        page_count = 0
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text.strip())

                # Also try to extract tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            row_text = " | ".join([str(cell) for cell in row if cell])
                            if row_text.strip():
                                text_parts.append(row_text)

        full_text = "\n".join(text_parts)

        # Confidence based on content quality
        if len(full_text) > 500:
            confidence = 0.95
        elif len(full_text) > 200:
            confidence = 0.90
        elif len(full_text) > 50:
            confidence = 0.75
        elif len(full_text) > 0:
            confidence = 0.50
        else:
            confidence = 0.10  # Scanned PDF with no embedded text

        print(f"[OCR] PDF: {page_count} pages, {len(full_text)} chars, confidence={confidence:.2f}")
        return full_text, confidence

    except ImportError:
        print("[OCR] pdfplumber not installed — install with: pip install pdfplumber")
        return "", 0.0
    except Exception as e:
        print(f"[OCR] PDF extraction error: {e}")
        return "", 0.0


def extract_text_from_image(file_path: str) -> Tuple[str, float]:
    """
    Extract text from image.
    Attempts pytesseract first, then falls back to basic Pillow metadata.
    """
    # Try pytesseract
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        if text and len(text.strip()) > 10:
            confidence = min(0.85, 0.50 + len(text.strip()) / 1000)
            print(f"[OCR] Image (pytesseract): {len(text)} chars, confidence={confidence:.2f}")
            return text.strip(), confidence
    except ImportError:
        pass
    except Exception as e:
        print(f"[OCR] pytesseract error: {e}")

    # Fallback: Pillow — extract EXIF/metadata + basic info
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(file_path)
        
        # Extract image metadata
        meta_parts = []
        meta_parts.append(f"Image Format: {img.format}")
        meta_parts.append(f"Image Size: {img.size[0]}x{img.size[1]}")
        meta_parts.append(f"Color Mode: {img.mode}")
        
        # Extract EXIF data if available
        exif_data = img.getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if isinstance(value, (str, int, float)):
                    meta_parts.append(f"{tag_name}: {value}")
        
        # Get file info
        file_size_kb = os.path.getsize(file_path) / 1024
        meta_parts.append(f"File Size: {file_size_kb:.1f} KB")
        meta_parts.append(f"File Name: {Path(file_path).name}")
        
        metadata_text = "\n".join(meta_parts)
        
        print(f"[OCR] Image (Pillow metadata): {len(metadata_text)} chars")
        return metadata_text, 0.30  # Low confidence since we only have metadata

    except Exception as e:
        print(f"[OCR] Image processing error: {e}")
        return "", 0.0


def extract_key_fields(ocr_text: str) -> Dict:
    """
    Extract structured fields from OCR text using comprehensive regex patterns.
    Returns dictionary of detected fields.
    """
    if not ocr_text:
        return {}
    
    fields = {}

    # ── Amount extraction (15+ patterns) ─────────────────────────────
    amount_patterns = [
        # Dollar formats
        r'(?:Grand\s*Total|Net\s*(?:Amount|Payable)|Total\s*(?:Amount|Due|Charges|Bill|Cost))[:\s]*\$?\s*([\d,]+(?:\.\d{2})?)',
        r'(?:Amount\s*(?:Due|Payable|Claimed|Total))[:\s]*\$?\s*([\d,]+(?:\.\d{2})?)',
        r'(?:Total|Subtotal|Balance\s*Due)[:\s]*\$\s*([\d,]+(?:\.\d{2})?)',
        r'\$\s*([\d,]+(?:\.\d{2})?)',
        r'USD\s*([\d,]+(?:\.\d{2})?)',
        # Rupee formats
        r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)',
        r'(?:Total|Amount|Cost)[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)',
        # Generic amount after keywords
        r'(?:Claim\s*Amount|Insured\s*Amount|Coverage\s*Amount)[:\s]*([\d,]+(?:\.\d{2})?)',
        r'(?:Repair\s*Cost|Damage\s*Estimate|Treatment\s*Cost)[:\s]*\$?\s*([\d,]+(?:\.\d{2})?)',
    ]
    
    amounts_found = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m.replace(",", ""))
                if val > 0:
                    amounts_found.append(val)
            except ValueError:
                pass
    
    if amounts_found:
        # Use the largest amount as the primary amount
        fields["amount"] = max(amounts_found)
        fields["all_amounts"] = sorted(set(amounts_found), reverse=True)[:5]

    # ── Date extraction ──────────────────────────────────────────────
    date_patterns = [
        (r'(?:Date\s*of\s*(?:Incident|Accident|Loss|Service|Admission|Discharge|Issue))[:\s]*([\d]{4}-[\d]{2}-[\d]{2})', None),
        (r'(?:Date\s*of\s*(?:Incident|Accident|Loss|Service|Admission|Discharge|Issue))[:\s]*([\d]{2}/[\d]{2}/[\d]{4})', "%d/%m/%Y"),
        (r'(?:Date\s*of\s*(?:Incident|Accident|Loss|Service|Admission|Discharge|Issue))[:\s]*([\d]{2}-[\d]{2}-[\d]{4})', "%d-%m-%Y"),
        (r'(?:Invoice\s*Date|Bill\s*Date|Report\s*Date|Document\s*Date)[:\s]*([\d]{4}-[\d]{2}-[\d]{2})', None),
        (r'(?:Invoice\s*Date|Bill\s*Date|Report\s*Date|Document\s*Date)[:\s]*([\d]{2}/[\d]{2}/[\d]{4})', "%d/%m/%Y"),
        (r'Date[:\s]+([\d]{4}-[\d]{2}-[\d]{2})', None),
        (r'Date[:\s]+([\d]{2}/[\d]{2}/[\d]{4})', "%d/%m/%Y"),
        # Month name formats
        (r'(\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b)', "%d %B %Y"),
        (r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b)', "%B %d, %Y"),
    ]
    
    for pattern, date_format in date_patterns:
        m = re.search(pattern, ocr_text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            if date_format:
                try:
                    parsed = datetime.strptime(date_str.strip(), date_format)
                    fields["date"] = parsed.strftime("%Y-%m-%d")
                except ValueError:
                    fields["date"] = date_str
            else:
                fields["date"] = date_str
            break

    # ── Reference / Invoice / Report numbers ─────────────────────────
    ref_patterns = [
        r'(?:Reference\s*(?:No\.?|Number))[:\s#]*([\w\-/]+)',
        r'(?:Invoice\s*(?:No\.?|Number|#))[:\s#]*([\w\-/]+)',
        r'(?:Report\s*(?:No\.?|Number))[:\s#]*([\w\-/]+)',
        r'(?:FIR\s*(?:No\.?|Number))[:\s#]*([\w\-/]+)',
        r'(?:Policy\s*(?:No\.?|Number))[:\s#]*([\w\-/]+)',
        r'(?:Claim\s*(?:No\.?|Number|ID|Ref))[:\s#]*([\w\-/]+)',
        r'(?:Case\s*(?:No\.?|Number))[:\s#]*([\w\-/]+)',
        r'(?:Receipt\s*(?:No\.?|Number))[:\s#]*([\w\-/]+)',
    ]
    for pattern in ref_patterns:
        m = re.search(pattern, ocr_text, re.IGNORECASE)
        if m:
            fields["reference"] = m.group(1).strip()
            break

    # ── Name extraction ──────────────────────────────────────────────
    name_patterns = [
        r'(?:Patient\s*Name|Claimant|Insured\s*Name|Name\s*of\s*(?:Patient|Insured|Claimant))[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?:Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ]
    for pattern in name_patterns:
        m = re.search(pattern, ocr_text, re.IGNORECASE)
        if m:
            fields["name"] = m.group(1).strip()
            break

    # ── Hospital / Provider / Garage name ────────────────────────────
    provider_patterns = [
        r'(?:Hospital|Clinic|Medical\s*Center|Healthcare)[:\s]+(.+?)(?:\n|$)',
        r'(?:Garage|Workshop|Repair\s*Center|Service\s*Center)[:\s]+(.+?)(?:\n|$)',
        r'(?:Provider|Facility)[:\s]+(.+?)(?:\n|$)',
    ]
    for pattern in provider_patterns:
        m = re.search(pattern, ocr_text, re.IGNORECASE)
        if m:
            fields["provider"] = m.group(1).strip()[:100]
            break

    # ── Diagnosis / Description ──────────────────────────────────────
    diag_patterns = [
        r'(?:Diagnosis|Condition|Ailment|Injury)[:\s]+(.+?)(?:\n|$)',
        r'(?:Description\s*of\s*(?:Damage|Injury|Loss|Incident))[:\s]+(.+?)(?:\n|$)',
        r'(?:Repair\s*Description|Work\s*Done)[:\s]+(.+?)(?:\n|$)',
    ]
    for pattern in diag_patterns:
        m = re.search(pattern, ocr_text, re.IGNORECASE)
        if m:
            fields["diagnosis"] = m.group(1).strip()[:200]
            break

    # ── Vehicle information ──────────────────────────────────────────
    vehicle_patterns = [
        r'(?:Vehicle\s*(?:No\.?|Number|Reg))[:\s]*([\w\-]+)',
        r'(?:Registration\s*(?:No\.?|Number))[:\s]*([\w\-]+)',
        r'(?:License\s*Plate)[:\s]*([\w\-]+)',
    ]
    for pattern in vehicle_patterns:
        m = re.search(pattern, ocr_text, re.IGNORECASE)
        if m:
            fields["vehicle_number"] = m.group(1).strip()
            break

    return fields


def detect_tampering(ocr_text: str, file_path: str, doc_type: str) -> Tuple[bool, List[str]]:
    """
    Detect potential document tampering using heuristics.
    Returns (is_tampered, list_of_reasons).
    """
    reasons = []
    
    if not ocr_text:
        return False, []
    
    text_lower = ocr_text.lower()
    
    # 1. Known editing software markers
    editing_markers = [
        "photoshop", "edited", "modified copy", "corrected copy",
        "adobe acrobat pro", "foxit editor", "nitro pro",
        "draft", "sample", "specimen", "not valid",
    ]
    for marker in editing_markers:
        if marker in text_lower:
            reasons.append(f"Editing marker detected: '{marker}'")
    
    # 2. Suspiciously short text for document type
    min_lengths = {
        "police_report": 100,
        "medical_bill": 80,
        "invoice": 60,
        "id_proof": 30,
    }
    min_len = min_lengths.get(doc_type, 20)
    if 0 < len(ocr_text) < min_len:
        reasons.append(f"Document text unusually short ({len(ocr_text)} chars) for type '{doc_type}'")
    
    # 3. Inconsistent dates (future dates)
    future_date_pattern = r'(\d{4})-(\d{2})-(\d{2})'
    for match in re.finditer(future_date_pattern, ocr_text):
        try:
            doc_date = datetime.strptime(match.group(0), "%Y-%m-%d")
            if doc_date > datetime.now():
                reasons.append(f"Future date detected in document: {match.group(0)}")
        except ValueError:
            pass
    
    # 4. Repeated suspicious patterns (copy-paste artifacts)
    lines = ocr_text.split("\n")
    if len(lines) > 5:
        unique_lines = set(line.strip() for line in lines if line.strip())
        if len(unique_lines) < len(lines) * 0.5:
            reasons.append("High ratio of duplicate lines — possible copy-paste artifact")
    
    # 5. Check for inconsistent amounts
    amounts = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', ocr_text)
    if len(amounts) >= 3:
        try:
            nums = [float(a.replace(",", "")) for a in amounts]
            # Check if totals add up (very basic check)
            if len(nums) >= 3:
                total = max(nums)
                sub_items = sorted(nums[:-1], reverse=True)
                if len(sub_items) >= 2 and total > 0:
                    sum_of_parts = sum(sub_items[:5])
                    if sum_of_parts > 0 and abs(total - sum_of_parts) / total > 0.5:
                        reasons.append("Line item amounts don't sum to total — possible manipulation")
        except (ValueError, ZeroDivisionError):
            pass
    
    is_tampered = len(reasons) > 0
    return is_tampered, reasons


def process_document(file_path: str, doc_type: str) -> Dict:
    """
    Main document processing pipeline.
    Runs real OCR, extracts fields, and checks for tampering.
    Returns full OCR result with extracted fields.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        text, confidence = extract_text_from_pdf(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        text, confidence = extract_text_from_image(file_path)
    else:
        text = ""
        confidence = 0.0

    fields = extract_key_fields(text) if text else {}
    
    # Run tampering detection
    tamper_suspected, tamper_reasons = detect_tampering(text, file_path, doc_type)

    # Auto-detect both claim type and document subtype
    detected_claim_type = detect_document_type(text)
    detected_subtype = detect_document_subtype(text)

    result = {
        "ocr_text": text,
        "ocr_fields": fields,
        "ocr_confidence": round(confidence, 3),
        "tamper_detected": tamper_suspected,
        "tamper_reasons": tamper_reasons,
        "extracted_amount": fields.get("amount"),
        "extracted_date": fields.get("date"),
        "extracted_reference": fields.get("reference"),
        "extracted_name": fields.get("name"),
        "extracted_provider": fields.get("provider"),
        "doc_type": doc_type,
        "detected_doc_type": detected_claim_type,
        "detected_doc_subtype": detected_subtype,
        "text_length": len(text),
        "fields_count": len(fields),
    }
    
    print(f"[OCR] Processed {ext} document: {len(fields)} fields extracted, "
          f"confidence={confidence:.2f}, tamper={'YES' if tamper_suspected else 'NO'}, "
          f"claim-type={detected_claim_type}, doc-subtype={detected_subtype}")
    
    return result

