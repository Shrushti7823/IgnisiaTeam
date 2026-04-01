"""
ClaimIQ - Image Fraud Detection Service
========================================
Three capabilities:
  1. Perceptual Hashing (pHash + dHash) for duplicate detection
  2. Cross-claim image duplicate search
  3. Signature/stamp presence detection (pixel-density heuristics)

All CPU-friendly, no GPU required.
"""
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from backend.core.config import settings


# ═══════════════════════════════════════════════════════════════════════
# 1. PERCEPTUAL IMAGE HASHING
# ═══════════════════════════════════════════════════════════════════════

def compute_image_hashes(file_path: str) -> Dict[str, Optional[str]]:
    """
    Compute pHash and dHash for an image file.
    Returns {"phash": "hex_string", "dhash": "hex_string"} or None values on failure.
    """
    try:
        import imagehash
        from PIL import Image

        img = Image.open(file_path)

        # Convert to RGB if necessary (handles RGBA, P mode, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        phash = str(imagehash.phash(img))
        dhash = str(imagehash.dhash(img))

        print(f"[ImageFraud] Hashes computed: pHash={phash[:12]}..., dHash={dhash[:12]}...")
        return {"phash": phash, "dhash": dhash}

    except ImportError:
        print("[ImageFraud] imagehash library not installed — pip install imagehash")
        return {"phash": None, "dhash": None}
    except Exception as e:
        print(f"[ImageFraud] Hash computation error: {e}")
        return {"phash": None, "dhash": None}


def compute_hash_from_pdf_images(file_path: str) -> List[Dict[str, Optional[str]]]:
    """
    Extract images from a PDF and compute hashes for each.
    Returns list of hash dicts, one per extracted image.
    """
    hashes = []
    try:
        import pdfplumber
        from PIL import Image
        import io

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages[:5]):  # Limit to first 5 pages
                images = page.images
                if images:
                    # Use the page as an image
                    page_img = page.to_image(resolution=150)
                    # Save to temp and hash
                    temp_path = file_path + f"_page{page_num}.png"
                    page_img.save(temp_path)
                    h = compute_image_hashes(temp_path)
                    hashes.append(h)
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
    except Exception as e:
        print(f"[ImageFraud] PDF image extraction error: {e}")

    return hashes


# ═══════════════════════════════════════════════════════════════════════
# 2. DUPLICATE IMAGE DETECTION (Cross-Claim)
# ═══════════════════════════════════════════════════════════════════════

def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    try:
        import imagehash
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2  # imagehash overloads __sub__ for Hamming distance
    except ImportError:
        # Fallback: manual computation
        if len(hash1) != len(hash2):
            return 999
        diff = 0
        for c1, c2 in zip(hash1, hash2):
            b1 = int(c1, 16)
            b2 = int(c2, 16)
            xor = b1 ^ b2
            diff += bin(xor).count("1")
        return diff
    except Exception:
        return 999


def find_duplicate_images(
    phash: str,
    dhash: str,
    existing_hashes: List[Dict],
    current_claim_id: int,
    threshold: Optional[int] = None,
) -> List[Dict]:
    """
    Compare an image's hashes against all existing image hashes in the database.

    Args:
        phash: pHash of the new image
        dhash: dHash of the new image
        existing_hashes: list of {"claim_id", "document_id", "phash", "dhash"}
        current_claim_id: the claim this image belongs to (exclude self-matches)
        threshold: max Hamming distance to consider a "duplicate"

    Returns:
        List of matches with distance info.
    """
    if not phash or not dhash:
        return []

    threshold = threshold or settings.IMAGE_HASH_DISTANCE_THRESHOLD
    matches = []

    for existing in existing_hashes:
        # Skip documents from the same claim
        if existing.get("claim_id") == current_claim_id:
            continue

        ex_phash = existing.get("phash")
        ex_dhash = existing.get("dhash")

        if not ex_phash or not ex_dhash:
            continue

        p_dist = hamming_distance(phash, ex_phash)
        d_dist = hamming_distance(dhash, ex_dhash)

        # Both hashes must be close for a confident match
        if p_dist <= threshold and d_dist <= threshold:
            matches.append({
                "matched_claim_id": existing["claim_id"],
                "matched_document_id": existing["document_id"],
                "phash_distance": p_dist,
                "dhash_distance": d_dist,
                "confidence": round(1.0 - (min(p_dist, d_dist) / max(threshold, 1)), 2),
            })

    if matches:
        print(f"[ImageFraud] ⚠️ Found {len(matches)} duplicate image(s)!")
    return matches


# ═══════════════════════════════════════════════════════════════════════
# 3. SIGNATURE / STAMP PRESENCE DETECTION
# ═══════════════════════════════════════════════════════════════════════

def detect_signature_stamp(file_path: str, doc_type: str = "invoice") -> Dict:
    """
    Detect whether a document image contains a signature and/or stamp
    using pixel-density heuristics (no CNN, CPU-friendly).

    Strategy:
      - Signatures are typically in the bottom 30% of a document
      - They appear as dark ink strokes on light background
      - Stamps are circular/rectangular ink regions with specific color profiles
      - We analyze pixel intensity distribution in the target zone

    Returns:
        {
            "has_signature": bool,
            "has_stamp": bool,
            "signature_confidence": float (0–1),
            "stamp_confidence": float (0–1),
            "analysis_details": str,
        }
    """
    result = {
        "has_signature": None,
        "has_stamp": None,
        "signature_confidence": 0.0,
        "stamp_confidence": 0.0,
        "analysis_details": "",
    }

    try:
        from PIL import Image
        import numpy as np

        img = Image.open(file_path)

        # Convert to grayscale for analysis
        gray = img.convert("L")
        width, height = gray.size

        if width < 50 or height < 50:
            result["analysis_details"] = "Image too small for analysis"
            return result

        gray_array = np.array(gray)

        # ── Signature detection: bottom 30% of image ──────────────────
        sig_zone_start = int(height * 0.7)
        sig_zone = gray_array[sig_zone_start:, :]

        if sig_zone.size > 0:
            # Count dark pixels (ink) in signature zone
            # Threshold: pixels darker than 80 (out of 255)
            dark_pixels = np.sum(sig_zone < 80)
            total_pixels = sig_zone.size
            dark_ratio = dark_pixels / total_pixels

            # Signatures typically have 2–15% dark pixel density
            # Too low = blank, too high = printed text/solid region
            if 0.02 <= dark_ratio <= 0.15:
                # Check for stroke-like patterns (variance in dark pixel positions)
                dark_positions = np.where(sig_zone < 80)
                if len(dark_positions[0]) > 20:
                    # Calculate spatial spread of dark pixels
                    row_spread = np.std(dark_positions[0])
                    col_spread = np.std(dark_positions[1])

                    # Signatures have moderate spread (not concentrated in one spot)
                    if row_spread > 5 and col_spread > 10:
                        result["has_signature"] = True
                        result["signature_confidence"] = min(0.85, dark_ratio * 8)
                    else:
                        result["has_signature"] = False
                        result["signature_confidence"] = 0.2
                else:
                    result["has_signature"] = False
                    result["signature_confidence"] = 0.1
            elif dark_ratio < 0.02:
                result["has_signature"] = False
                result["signature_confidence"] = 0.05
            else:
                # Could be heavy text or a large stamp
                result["has_signature"] = True
                result["signature_confidence"] = 0.5

        # ── Stamp detection: look for colored ink regions ─────────────
        rgb_img = img.convert("RGB")
        rgb_array = np.array(rgb_img)

        # Stamps are typically blue, red, or dark purple
        # Check bottom 40% of image for colored regions
        stamp_zone_start = int(height * 0.6)
        stamp_zone = rgb_array[stamp_zone_start:, :]

        if stamp_zone.size > 0:
            r, g, b = stamp_zone[:,:,0], stamp_zone[:,:,1], stamp_zone[:,:,2]

            # Blue stamp detection (common in official documents)
            blue_mask = (b > 100) & (b > r + 30) & (b > g + 30)
            blue_ratio = np.sum(blue_mask) / (stamp_zone.shape[0] * stamp_zone.shape[1])

            # Red stamp detection
            red_mask = (r > 100) & (r > b + 30) & (r > g + 30)
            red_ratio = np.sum(red_mask) / (stamp_zone.shape[0] * stamp_zone.shape[1])

            stamp_ratio = max(blue_ratio, red_ratio)

            if stamp_ratio > 0.005:  # At least 0.5% colored pixels
                result["has_stamp"] = True
                result["stamp_confidence"] = min(0.90, stamp_ratio * 50)
            else:
                result["has_stamp"] = False
                result["stamp_confidence"] = 0.1

        details = []
        if result["has_signature"]:
            details.append(f"Signature detected (conf: {result['signature_confidence']:.0%})")
        else:
            details.append("No signature detected")
        if result["has_stamp"]:
            details.append(f"Stamp detected (conf: {result['stamp_confidence']:.0%})")
        else:
            details.append("No stamp detected")

        result["analysis_details"] = "; ".join(details)
        print(f"[ImageFraud] {result['analysis_details']}")

    except ImportError:
        result["analysis_details"] = "Pillow/numpy not available for image analysis"
    except Exception as e:
        result["analysis_details"] = f"Analysis error: {str(e)}"
        print(f"[ImageFraud] Signature/stamp detection error: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════════
# 4. FULL IMAGE FRAUD PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def run_image_fraud_check(
    file_path: str,
    doc_type: str,
    claim_id: int,
    existing_hashes: List[Dict],
) -> Dict:
    """
    Run the complete image fraud pipeline on a single file.

    Returns:
        {
            "phash": str,
            "dhash": str,
            "duplicates_found": list,
            "is_duplicate": bool,
            "signature_stamp": dict,
            "fraud_signals": list,
        }
    """
    ext = Path(file_path).suffix.lower()
    fraud_signals = []

    # Step 1: Compute hashes
    if ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        hashes = compute_image_hashes(file_path)
    elif ext == ".pdf":
        pdf_hashes = compute_hash_from_pdf_images(file_path)
        hashes = pdf_hashes[0] if pdf_hashes else {"phash": None, "dhash": None}
    else:
        hashes = {"phash": None, "dhash": None}

    # Step 2: Check for duplicates
    duplicates = []
    if hashes["phash"] and hashes["dhash"]:
        duplicates = find_duplicate_images(
            phash=hashes["phash"],
            dhash=hashes["dhash"],
            existing_hashes=existing_hashes,
            current_claim_id=claim_id,
        )
        if duplicates:
            fraud_signals.append({
                "type": "DUPLICATE_IMAGE",
                "severity": "critical",
                "message": f"Image matches {len(duplicates)} document(s) from other claims",
                "details": duplicates,
            })

    # Step 3: Signature/stamp detection (for document types that should have them)
    sig_stamp = {"has_signature": None, "has_stamp": None,
                 "signature_confidence": 0, "stamp_confidence": 0}
    docs_needing_signature = ["invoice", "medical_bill", "police_report", "id_proof"]

    if doc_type in docs_needing_signature and ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        sig_stamp = detect_signature_stamp(file_path, doc_type)

        if sig_stamp.get("has_signature") is False and doc_type in ["invoice", "medical_bill"]:
            fraud_signals.append({
                "type": "MISSING_SIGNATURE",
                "severity": "high",
                "message": f"Expected signature not found on {doc_type}",
            })

        if sig_stamp.get("has_stamp") is False and doc_type in ["invoice", "medical_bill", "police_report"]:
            fraud_signals.append({
                "type": "MISSING_STAMP",
                "severity": "medium",
                "message": f"Expected official stamp not found on {doc_type}",
            })

    return {
        "phash": hashes.get("phash"),
        "dhash": hashes.get("dhash"),
        "duplicates_found": duplicates,
        "is_duplicate": len(duplicates) > 0,
        "signature_stamp": sig_stamp,
        "fraud_signals": fraud_signals,
    }
