"""
ClaimIQ - Explainability Service
Generates human-readable AI decision explanations for each claim
"""
from typing import Dict, List, Optional


def generate_explainability_report(
    claim_amount: float,
    policy_limit: float,
    fraud_score: float,
    risk_score: float,
    confidence_score: float,
    decision: str,
    triggered_rules: List[Dict],
    eligibility_passed: bool,
    docs_verified: bool,
    settlement_notes: str = "",
    approved_amount: float = 0,
    deductible: float = 0,
) -> Dict:
    """
    Generate a structured Explainable AI report for a claim decision.
    Returns a rich JSON document explaining WHY the decision was made.
    """

    # Build factors list
    factors = []

    # Amount analysis
    ratio = claim_amount / max(policy_limit, 1)
    if ratio >= 0.9:
        factors.append({
            "factor": f"Claim amount (${claim_amount:,.0f}) is {ratio*100:.0f}% of policy limit (${policy_limit:,.0f})",
            "impact": "HIGH",
            "direction": "NEGATIVE",
            "category": "amount_risk",
        })
    elif ratio >= 0.7:
        factors.append({
            "factor": f"Claim amount is {ratio*100:.0f}% of policy limit",
            "impact": "MEDIUM",
            "direction": "NEGATIVE",
            "category": "amount_risk",
        })
    else:
        factors.append({
            "factor": f"Claim amount is within normal range ({ratio*100:.0f}% of limit)",
            "impact": "LOW",
            "direction": "POSITIVE",
            "category": "amount_risk",
        })

    # Fraud factors from triggered rules
    for rule in triggered_rules:
        severity = rule.get("severity", "medium").upper()
        impact = "CRITICAL" if severity == "CRITICAL" else "HIGH" if severity == "HIGH" else "MEDIUM"
        factors.append({
            "factor": rule["description"],
            "impact": impact,
            "direction": "NEGATIVE",
            "category": "fraud_indicator",
            "rule_id": rule.get("rule_id", ""),
        })

    # Eligibility factor
    if eligibility_passed:
        factors.append({
            "factor": "All eligibility checks passed (policy active, claim type valid)",
            "impact": "LOW",
            "direction": "POSITIVE",
            "category": "eligibility",
        })
    else:
        factors.append({
            "factor": "Eligibility check failed — claim does not meet basic criteria",
            "impact": "CRITICAL",
            "direction": "NEGATIVE",
            "category": "eligibility",
        })

    # Document factor
    if docs_verified:
        factors.append({
            "factor": "All required documents uploaded and verified",
            "impact": "LOW",
            "direction": "POSITIVE",
            "category": "documentation",
        })
    else:
        factors.append({
            "factor": "Missing or unverified documents",
            "impact": "MEDIUM",
            "direction": "NEGATIVE",
            "category": "documentation",
        })

    # Risk breakdown
    fraud_risk = min(fraud_score, 100)
    amount_risk = min(ratio * 100, 100)
    behavioral_risk = min(len(triggered_rules) * 15, 100)

    # Generate summary
    summary = _generate_summary(decision, fraud_score, triggered_rules)

    # Generate recommendation
    recommendation = _generate_recommendation(decision, fraud_score, risk_score)

    # Human-readable bullet points
    bullet_points = _generate_bullet_points(decision, factors, fraud_score, approved_amount, claim_amount)

    return {
        "decision": decision.upper(),
        "confidence": round(confidence_score, 1),
        "summary": summary,
        "factors": factors,
        "rules_triggered_count": len(triggered_rules),
        "rules_triggered": triggered_rules,
        "risk_breakdown": {
            "fraud_risk": round(fraud_risk, 1),
            "amount_risk": round(amount_risk, 1),
            "behavioral_risk": round(behavioral_risk, 1),
            "overall_risk": round(risk_score, 1),
        },
        "settlement_details": {
            "claim_amount": claim_amount,
            "approved_amount": approved_amount,
            "deductible": deductible,
            "settlement_notes": settlement_notes,
        },
        "recommendation": recommendation,
        "bullet_points": bullet_points,
    }


def _generate_summary(decision: str, fraud_score: float, triggered_rules: list) -> str:
    """Generate a one-line human summary."""
    if decision in ("approved", "auto_approved"):
        if fraud_score < 20:
            return "Claim auto-approved. All verification gates passed with minimal risk indicators."
        return "Claim approved after standard verification. Low-to-moderate risk within acceptable thresholds."
    elif decision == "rejected":
        rule_count = len(triggered_rules)
        return f"Claim rejected due to {rule_count} high-risk indicator(s). Fraud score: {fraud_score:.0f}/100."
    else:
        return f"Claim flagged for manual review. {len(triggered_rules)} risk indicator(s) need adjuster assessment."


def _generate_recommendation(decision: str, fraud_score: float, risk_score: float) -> str:
    """Generate action recommendation."""
    if decision in ("approved", "auto_approved"):
        return "No further action required. Settlement can proceed."
    elif decision == "rejected":
        if fraud_score >= 80:
            return "Recommend SIU (Special Investigation Unit) referral for potential fraud."
        return "Claim denied. Policyholder may appeal with additional documentation."
    else:
        if fraud_score >= 60:
            return "Senior adjuster review recommended. Check all documentation thoroughly."
        return "Standard adjuster review. Verify key documents and approve if satisfactory."


def _generate_bullet_points(decision: str, factors: list, fraud_score: float,
                             approved_amount: float, claim_amount: float) -> List[str]:
    """Generate bullet point explanations for the UI."""
    bullets = []

    if decision in ("approved", "auto_approved"):
        bullets.append(f"✅ Claim approved for ${approved_amount:,.2f}")
        positive = [f for f in factors if f["direction"] == "POSITIVE"]
        for p in positive[:3]:
            bullets.append(f"✅ {p['factor']}")
        if fraud_score < 30:
            bullets.append(f"✅ Low fraud risk score ({fraud_score:.0f}/100)")
    elif decision == "rejected":
        bullets.append(f"❌ Claim of ${claim_amount:,.2f} has been rejected")
        negative = [f for f in factors if f["direction"] == "NEGATIVE"]
        for n in negative[:5]:
            bullets.append(f"❌ {n['factor']}")
        bullets.append(f"❌ Fraud risk score: {fraud_score:.0f}/100")
    else:
        bullets.append(f"⚠️ Claim requires manual review")
        negative = [f for f in factors if f["direction"] == "NEGATIVE"]
        for n in negative[:4]:
            bullets.append(f"⚠️ {n['factor']}")
        positive = [f for f in factors if f["direction"] == "POSITIVE"]
        for p in positive[:2]:
            bullets.append(f"✅ {p['factor']}")

    return bullets
