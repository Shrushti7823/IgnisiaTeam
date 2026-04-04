"""
ClaimIQ - Pipeline Service (Production)
=========================================
Orchestrates the 6-stage real-time claim processing pipeline
with full hard/soft rule engine, ML fraud probability, and image fraud detection.

Stages:
  1. Claim Submitted
  2. Document Verification (+ image fraud scan)
  3. Fraud Analysis (hard rules + soft scoring + ML probability)
  4. Risk Scoring
  5. Decision Engine (combined logic)
  6. Settlement (or Human Review queue)
"""
import time
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_new_session
from backend.models.claim import Claim
from backend.models.user import User
from backend.models.document import Document, FraudAlert
from backend.services.audit_service import log_event
from backend.services.explainability_service import generate_explainability_report
from backend.services.stp_engine import (
    check_eligibility,
    check_documents,
    run_fraud_assessment,
    calculate_settlement,
    make_stp_decision,
    get_required_docs,
)


PIPELINE_STAGES = [
    "submitted",
    "document_verification",
    "fraud_analysis",
    "risk_scoring",
    "decision_engine",
    "settlement",
]


def run_pipeline_sync(claim_id: int, db: Session):
    """
    Synchronous pipeline runner (called in background task).
    Runs all 6 stages sequentially with real-time status updates.
    Now includes image fraud detection and hard/soft rule engine.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return

    user = db.query(User).filter(User.id == claim.user_id).first()
    if not user:
        return

    delay = settings.PIPELINE_STAGE_DELAY

    try:
        _execute_pipeline(claim, user, db, delay)
    except Exception as e:
        print(f"[Pipeline] CRITICAL ERROR in pipeline for claim {claim_id}: {e}")
        import traceback
        traceback.print_exc()
        # Make sure the claim doesn't stay stuck
        try:
            claim.current_stage = "completed"
            claim.status = "pending_admin_approval"
            claim.settlement_notes = (claim.settlement_notes or "") + f" | Pipeline error: {str(e)[:200]}"
            claim.processed_at = datetime.utcnow()
            claim.stage_settled_at = datetime.utcnow()
            db.commit()
        except Exception:
            pass


def _execute_pipeline(claim, user, db, delay):
    """Inner pipeline execution — separated so errors can be caught."""

    # ── STAGE 1: Submitted ──────────────────────────────────────────
    start = time.time()
    claim.current_stage = "submitted"
    claim.submitted_at = claim.submitted_at or datetime.utcnow()
    db.commit()

    log_event(db, claim.id, "submitted", "Claim submitted and queued for processing", {
        "claim_reference": claim.claim_reference,
        "claim_type": claim.claim_type,
        "claim_amount": claim.claim_amount,
    }, duration_ms=(time.time() - start) * 1000)

    time.sleep(delay)

    # ── STAGE 2: Document Verification + Image Fraud Scan ───────────
    start = time.time()
    claim.current_stage = "document_verification"
    db.commit()

    uploaded_types = [
        doc.doc_type for doc in claim.documents
    ] if claim.documents else []
    docs_ok, docs_msg = check_documents(claim, uploaded_types)
    claim.documents_verified = docs_ok
    claim.stage_doc_verified_at = datetime.utcnow()

    # Run image fraud detection on all uploaded images
    duplicate_image_detected = False
    signature_stamp_failed = False
    image_fraud_signals = []

    try:
        from backend.services.image_fraud_service import run_image_fraud_check

        # Get all existing image hashes for cross-claim comparison
        all_docs = db.query(Document).filter(
            Document.image_phash.isnot(None),
            Document.claim_id != claim_id,
        ).all()
        existing_hashes = [
            {"claim_id": d.claim_id, "document_id": d.id,
             "phash": d.image_phash, "dhash": d.image_dhash}
            for d in all_docs
        ]

        for doc in (claim.documents or []):
            if doc.file_path and doc.file_path.strip():
                result = run_image_fraud_check(
                    file_path=doc.file_path,
                    doc_type=doc.doc_type or "other",
                    claim_id=claim_id,
                    existing_hashes=existing_hashes,
                )

                # Save hashes to document record
                doc.image_phash = result.get("phash")
                doc.image_dhash = result.get("dhash")

                sig_stamp = result.get("signature_stamp", {})
                doc.has_signature = sig_stamp.get("has_signature")
                doc.has_stamp = sig_stamp.get("has_stamp")

                if result.get("is_duplicate"):
                    duplicate_image_detected = True

                for signal in result.get("fraud_signals", []):
                    image_fraud_signals.append(signal)
                    if signal["type"] == "MISSING_SIGNATURE":
                        signature_stamp_failed = True
                    elif signal["type"] == "MISSING_STAMP":
                        signature_stamp_failed = True

        db.commit()
    except Exception as e:
        print(f"[Pipeline] Image fraud check error: {e}")

    claim.duplicate_image_detected = duplicate_image_detected

    log_event(db, claim.id, "document_verification",
              f"Document check: {'PASSED' if docs_ok else 'INCOMPLETE'}", {
                  "verified": docs_ok,
                  "message": docs_msg,
                  "uploaded_types": uploaded_types,
                  "document_count": len(uploaded_types),
                  "duplicate_image_detected": duplicate_image_detected,
                  "image_fraud_signals": len(image_fraud_signals),
              }, duration_ms=(time.time() - start) * 1000)

    db.commit()
    time.sleep(delay)

    # ── STAGE 3: Fraud Analysis (Hard + Soft + ML) ──────────────────
    start = time.time()
    claim.current_stage = "fraud_analysis"
    db.commit()

    # Get OCR data from uploaded documents
    ocr_amount = None
    ocr_date = None
    provider_name = None
    doc_count = len(claim.documents) if claim.documents else 0
    if claim.documents:
        for doc in claim.documents:
            if doc.ocr_fields and isinstance(doc.ocr_fields, dict):
                if "amount" in doc.ocr_fields and ocr_amount is None:
                    ocr_amount = doc.ocr_fields["amount"]
                if "date" in doc.ocr_fields and ocr_date is None:
                    ocr_date = doc.ocr_fields["date"]
                if "provider" in doc.ocr_fields and provider_name is None:
                    provider_name = doc.ocr_fields["provider"]

    # Run full production fraud assessment
    fraud_result = run_fraud_assessment(
        claim=claim,
        user=user,
        ocr_amount=ocr_amount,
        doc_count=doc_count,
        ocr_date=ocr_date,
        provider_name=provider_name,
        uploaded_doc_types=uploaded_types,
        is_duplicate_claim=False,  # Would need claim ref dedup check
        signature_stamp_failed=signature_stamp_failed,
        duplicate_image_detected=duplicate_image_detected,
    )

    claim.fraud_score = fraud_result["fraud_score"]
    claim.fraud_cleared = fraud_result["fraud_score"] < 70

    # Save production scoring fields
    claim.hard_rule_violated = fraud_result.get("hard_rule_violated")
    claim.soft_rule_score = fraud_result.get("soft_score")
    claim.ml_fraud_probability = fraud_result.get("ml_probability")

    claim.stage_fraud_analyzed_at = datetime.utcnow()

    # Save fraud alerts
    for rule in fraud_result["triggered_rules"]:
        alert = FraudAlert(
            claim_id=claim.id,
            rule_id=rule["rule_id"],
            rule_name=rule["rule_name"],
            severity=rule["severity"],
            description=rule.get("description", ""),
            score_impact=rule.get("score_impact", 0),
        )
        db.add(alert)

    claim.fraud_flags = fraud_result["triggered_rules"]
    db.commit()

    log_event(db, claim.id, "fraud_analysis",
              f"Fraud analysis complete — Score: {fraud_result['fraud_score']:.1f}/100", {
                  "fraud_score": fraud_result["fraud_score"],
                  "rule_score": fraud_result["rule_score"],
                  "ml_score": fraud_result.get("ml_score"),
                  "soft_score": fraud_result.get("soft_score"),
                  "ml_probability": fraud_result.get("ml_probability"),
                  "hard_rule_violated": fraud_result.get("hard_rule_violated"),
                  "verdict": fraud_result["verdict"],
                  "rules_triggered": len(fraud_result["triggered_rules"]),
                  "combined_decision": fraud_result.get("combined_decision", {}).get("decision"),
              }, duration_ms=(time.time() - start) * 1000)

    time.sleep(delay)

    # ── Check for hard rule instant rejection ───────────────────────
    combined = fraud_result.get("combined_decision", {})
    if combined.get("override") and combined.get("decision") == "rejected":
        # Short-circuit: hard rule or duplicate image → instant reject
        _handle_instant_rejection(claim, user, fraud_result, db, delay)
        return

    # ── STAGE 4: Risk Scoring ───────────────────────────────────────
    start = time.time()
    claim.current_stage = "risk_scoring"
    db.commit()

    eligible, eligibility_msg = check_eligibility(claim, user)
    claim.eligibility_passed = eligible
    claim.stp_eligible = eligible

    settlement = calculate_settlement(claim, user, fraud_result["fraud_score"])
    claim.risk_score = settlement["risk_score"]
    claim.approved_amount = settlement["approved_amount"]
    claim.deductible = settlement["deductible"]
    claim.stage_risk_scored_at = datetime.utcnow()
    db.commit()

    log_event(db, claim.id, "risk_scoring",
              f"Risk assessment: {settlement['risk_score']:.1f}/100 — Eligible: {eligible}", {
                  "eligible": eligible,
                  "eligibility_message": eligibility_msg,
                  "risk_score": settlement["risk_score"],
                  "approved_amount": settlement["approved_amount"],
                  "deductible": settlement["deductible"],
              }, duration_ms=(time.time() - start) * 1000)

    time.sleep(delay)

    # ── STAGE 5: Decision Engine ────────────────────────────────────
    start = time.time()
    claim.current_stage = "decision_engine"
    db.commit()

    # Use the combined decision from fraud assessment
    if combined.get("decision") in ("rejected", "manual_review", "auto_approved"):
        stp_decision = {
            "decision": combined["decision"],
            "reason": combined["reason"],
            "auto": combined.get("auto", False),
        }
    else:
        # Fallback to legacy STP decision
        stp_decision = make_stp_decision(
            eligible, docs_ok, fraud_result["fraud_score"], settlement["risk_score"]
        )

    claim.auto_decided = stp_decision["auto"]
    claim.settlement_notes = stp_decision["reason"]
    claim.stage_decision_at = datetime.utcnow()

    # Calculate confidence score
    if stp_decision["decision"] == "auto_approved":
        claim.confidence_score = max(95 - fraud_result["fraud_score"], 60)
    elif stp_decision["decision"] == "rejected":
        claim.confidence_score = min(50 + fraud_result["fraud_score"], 95)
    else:
        claim.confidence_score = 50 + (fraud_result["fraud_score"] * 0.3)

    db.commit()

    log_event(db, claim.id, "decision_engine",
              f"Decision: {stp_decision['decision'].upper()}", {
                  "decision": stp_decision["decision"],
                  "reason": stp_decision["reason"],
                  "auto_decided": stp_decision["auto"],
                  "confidence": claim.confidence_score,
                  "trigger": combined.get("trigger", "legacy"),
              }, duration_ms=(time.time() - start) * 1000)

    time.sleep(delay)

    # ── STAGE 6: Settlement ─────────────────────────────────────────
    start = time.time()
    claim.current_stage = "settlement"
    db.commit()

    if stp_decision["decision"] == "auto_approved":
        claim.status = "pending_admin_approval"
        claim.payout_status = "pending"
        claim.stage_settled_at = datetime.utcnow()
        claim.settlement_notes = (claim.settlement_notes or "") + " | AI Recommendation: APPROVE"
    elif stp_decision["decision"] == "rejected":
        claim.status = "pending_admin_approval"
        claim.payout_status = "pending"
        claim.stage_settled_at = datetime.utcnow()
        claim.settlement_notes = (claim.settlement_notes or "") + " | AI Recommendation: REJECT"
    else:
        claim.status = "pending_admin_approval"
        claim.payout_status = "pending"
        claim.stage_settled_at = datetime.utcnow()
        claim.settlement_notes = (claim.settlement_notes or "") + " | AI Recommendation: MANUAL REVIEW"

    claim.processed_at = datetime.utcnow()

    # Generate Explainability Report
    report = generate_explainability_report(
        claim_amount=claim.claim_amount,
        policy_limit=user.policy_limit or 10000,
        fraud_score=claim.fraud_score,
        risk_score=claim.risk_score,
        confidence_score=claim.confidence_score,
        decision=claim.status,
        triggered_rules=fraud_result["triggered_rules"],
        eligibility_passed=eligible,
        docs_verified=docs_ok,
        settlement_notes=claim.settlement_notes,
        approved_amount=claim.approved_amount,
        deductible=claim.deductible,
    )
    claim.explainability_report = report

    # Mark pipeline complete
    claim.current_stage = "completed"

    # Update user stats
    user.claim_count = (user.claim_count or 0) + 1
    if fraud_result["fraud_score"] >= 70:
        user.fraud_flags = (user.fraud_flags or 0) + 1

    db.commit()

    log_event(db, claim.id, "settlement",
              f"Pipeline complete — Status: {claim.status.upper()}", {
                  "final_status": claim.status,
                  "payout_status": claim.payout_status,
                  "approved_amount": claim.approved_amount,
                  "hard_rule_violated": claim.hard_rule_violated,
                  "soft_rule_score": claim.soft_rule_score,
                  "ml_fraud_probability": claim.ml_fraud_probability,
                  "explainability_generated": True,
              }, duration_ms=(time.time() - start) * 1000)


def _handle_instant_rejection(claim, user, fraud_result, db, delay):
    """Handle instant rejection from hard rule violation or duplicate image."""
    claim.current_stage = "risk_scoring"
    claim.eligibility_passed = False
    claim.stp_eligible = False
    claim.risk_score = 100.0
    claim.approved_amount = 0.0
    claim.deductible = 0.0
    claim.stage_risk_scored_at = datetime.utcnow()
    db.commit()
    time.sleep(delay * 0.5)

    claim.current_stage = "decision_engine"
    claim.auto_decided = True
    reason = fraud_result.get("combined_decision", {}).get("reason", "Hard rule violation")
    claim.settlement_notes = reason
    claim.confidence_score = 95.0
    claim.stage_decision_at = datetime.utcnow()
    db.commit()
    time.sleep(delay * 0.5)

    claim.current_stage = "settlement"
    claim.status = "rejected"
    claim.payout_status = "rejected"
    claim.processed_at = datetime.utcnow()
    claim.settled_at = datetime.utcnow()
    claim.stage_settled_at = datetime.utcnow()
    claim.current_stage = "completed"

    user.claim_count = (user.claim_count or 0) + 1

    report = generate_explainability_report(
        claim_amount=claim.claim_amount,
        policy_limit=user.policy_limit or 10000,
        fraud_score=claim.fraud_score,
        risk_score=100.0,
        confidence_score=95.0,
        decision="rejected",
        triggered_rules=fraud_result["triggered_rules"],
        eligibility_passed=False,
        docs_verified=claim.documents_verified or False,
        settlement_notes=reason,
        approved_amount=0.0,
        deductible=0.0,
    )
    claim.explainability_report = report
    db.commit()

    log_event(db, claim.id, "settlement",
              f"INSTANT REJECTION — {reason}", {
                  "final_status": "rejected",
                  "hard_rule_violated": claim.hard_rule_violated,
                  "override": True,
              })


def get_pipeline_status(claim_id: int, db: Session) -> Optional[Dict]:
    """Get current pipeline status for real-time tracking with rich per-stage data."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return None

    user = db.query(User).filter(User.id == claim.user_id).first()

    stages = []
    for stage_name in PIPELINE_STAGES:
        stage_info = {
            "name": stage_name,
            "label": _stage_label(stage_name),
            "status": "pending",
            "timestamp": None,
            "detail": None,
        }

        # Determine stage status
        stage_idx = PIPELINE_STAGES.index(stage_name)
        current_idx = PIPELINE_STAGES.index(claim.current_stage) if claim.current_stage in PIPELINE_STAGES else (len(PIPELINE_STAGES) if claim.current_stage == "completed" else 0)

        if stage_idx < current_idx:
            stage_info["status"] = "completed"
        elif stage_idx == current_idx:
            stage_info["status"] = "active"

        # Add timestamps
        ts_map = {
            "submitted": claim.submitted_at,
            "document_verification": claim.stage_doc_verified_at,
            "fraud_analysis": claim.stage_fraud_analyzed_at,
            "risk_scoring": claim.stage_risk_scored_at,
            "decision_engine": claim.stage_decision_at,
            "settlement": claim.stage_settled_at,
        }
        ts = ts_map.get(stage_name)
        if ts:
            stage_info["timestamp"] = ts.isoformat()
            if stage_info["status"] == "pending":
                stage_info["status"] = "completed"

        # Add per-stage detail data for completed/active stages
        if stage_info["status"] in ("completed", "active"):
            stage_info["detail"] = _get_stage_detail(stage_name, claim, user)

        stages.append(stage_info)

    return {
        "claim_id": claim.id,
        "claim_reference": claim.claim_reference,
        "current_stage": claim.current_stage,
        "status": claim.status,
        "stages": stages,
        "is_complete": claim.current_stage == "completed",
        "fraud_score": claim.fraud_score,
        "risk_score": claim.risk_score,
        "confidence_score": claim.confidence_score,
        "approved_amount": claim.approved_amount,
        "decision": claim.status,
        "explainability_report": claim.explainability_report,
        # Production fields
        "hard_rule_violated": claim.hard_rule_violated,
        "soft_rule_score": claim.soft_rule_score,
        "ml_fraud_probability": claim.ml_fraud_probability,
        "duplicate_image_detected": claim.duplicate_image_detected,
    }


def _get_stage_detail(stage_name: str, claim, user) -> Optional[Dict]:
    """Return rich detail data for a specific pipeline stage."""
    if stage_name == "submitted":
        return {
            "claim_type": claim.claim_type,
            "claim_amount": claim.claim_amount,
            "policy_number": claim.policy_number,
            "policy_limit": user.policy_limit if user else 10000,
            "amount_to_limit_pct": round((claim.claim_amount / max(user.policy_limit or 10000, 1)) * 100, 1) if user else 0,
            "incident_date": claim.incident_date,
        }
    elif stage_name == "document_verification":
        docs = []
        if claim.documents:
            for d in claim.documents:
                docs.append({
                    "doc_type": d.doc_type,
                    "file_name": d.file_name,
                    "ocr_confidence": d.ocr_confidence,
                    "is_verified": d.is_verified,
                    "tamper_detected": d.tamper_detected,
                    "has_signature": d.has_signature,
                    "has_stamp": d.has_stamp,
                    "detected_doc_type": d.detected_doc_type,
                    "image_duplicate": d.image_phash is not None,
                    "extracted_amount": d.ocr_fields.get("amount") if d.ocr_fields and isinstance(d.ocr_fields, dict) else None,
                    "extracted_date": d.ocr_fields.get("date") if d.ocr_fields and isinstance(d.ocr_fields, dict) else None,
                    "fields_count": len(d.ocr_fields) if d.ocr_fields and isinstance(d.ocr_fields, dict) else 0,
                })
        return {
            "documents": docs,
            "total_uploaded": len(docs),
            "all_verified": claim.documents_verified,
            "duplicate_image_detected": claim.duplicate_image_detected,
        }
    elif stage_name == "fraud_analysis":
        alerts = []
        if claim.fraud_alerts:
            for a in claim.fraud_alerts:
                alerts.append({
                    "rule_id": a.rule_id,
                    "rule_name": a.rule_name,
                    "severity": a.severity,
                    "score_impact": a.score_impact,
                    "description": a.description,
                })
        return {
            "fraud_score": claim.fraud_score,
            "fraud_cleared": claim.fraud_cleared,
            "hard_rule_violated": claim.hard_rule_violated,
            "soft_rule_score": claim.soft_rule_score,
            "ml_fraud_probability": claim.ml_fraud_probability,
            "triggered_rules": alerts,
            "rules_checked": 17,  # 5 hard + 12 soft
            "rules_triggered": len(alerts),
        }
    elif stage_name == "risk_scoring":
        return {
            "risk_score": claim.risk_score,
            "eligibility_passed": claim.eligibility_passed,
            "stp_eligible": claim.stp_eligible,
            "approved_amount": claim.approved_amount,
            "deductible": claim.deductible,
            "claim_amount": claim.claim_amount,
            "policy_limit": user.policy_limit if user else 10000,
        }
    elif stage_name == "decision_engine":
        return {
            "auto_decided": claim.auto_decided,
            "confidence_score": claim.confidence_score,
            "settlement_notes": claim.settlement_notes,
            "fraud_score": claim.fraud_score,
            "risk_score": claim.risk_score,
            "eligibility_passed": claim.eligibility_passed,
            "documents_verified": claim.documents_verified,
            "fraud_cleared": claim.fraud_cleared,
            "hard_rule_violated": claim.hard_rule_violated,
            "ml_fraud_probability": claim.ml_fraud_probability,
        }
    elif stage_name == "settlement":
        return {
            "status": claim.status,
            "approved_amount": claim.approved_amount,
            "payout_status": claim.payout_status,
            "deductible": claim.deductible,
            "claim_amount": claim.claim_amount,
        }
    return None


def _stage_label(stage: str) -> str:
    """Human-readable label for a pipeline stage."""
    labels = {
        "submitted": "Claim Submitted",
        "document_verification": "Document Verification",
        "fraud_analysis": "Fraud Analysis",
        "risk_scoring": "Risk Scoring",
        "decision_engine": "Decision Engine",
        "settlement": "Settlement",
    }
    return labels.get(stage, stage.replace("_", " ").title())
