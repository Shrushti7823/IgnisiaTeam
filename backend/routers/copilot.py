"""
ClaimIQ - Copilot Router
AI-powered claim assistant using Google Gemini API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.core.database import get_db
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.models.user import User

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    claim_type: Optional[str] = None
    claim_amount: Optional[float] = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: list = []


# Fallback rule-based responses when Gemini API is unavailable
FALLBACK_RESPONSES = {
    "auto": "For an **auto/vehicle claim**, you'll need:\n• Police FIR report 📋\n• Photos of the damage 📷\n• Repair invoice 💰\n\nClaims under $5,000 are eligible for STP (auto-approved in <5 min).\n\n**Estimated processing time:** Under 5 minutes for STP-eligible claims.",
    "health": "For a **health/medical claim**, please have:\n• Hospital bill & discharge summary 🏥\n• Doctor's prescription 💊\n• Your ID proof 🪪\n\nHealth claims under $5,000 qualify for auto-processing.\n\n**Tip:** Upload all documents during submission for fastest processing.",
    "travel": "For a **travel claim**, you'll need:\n• Booking confirmation ✈️\n• Cancellation/delay proof 📄\n• Your passport/ID 🪪\n\nTravel claims are typically processed in under 5 minutes via STP.",
    "property": "For a **property claim**, gather:\n• Damage photos 📷\n• Repair/replacement invoice 💰\n• Property documents & ID 📄\n\nProperty claims up to $5,000 qualify for automatic processing.",
    "documents": "**Required documents by claim type:**\n\n🚗 **Auto:** Police report, damage photos, repair invoice\n🏥 **Health:** Hospital bill, prescription, ID proof\n✈️ **Travel:** Booking confirmation, cancellation proof, passport\n🏠 **Property:** Damage photos, invoice, property docs, ID\n\nAll documents go through OCR extraction — no manual data entry needed!",
    "fraud": "**ClaimIQ's Fraud Detection System:**\n\n🧠 12-rule fraud engine + ML model\n📊 Each claim gets a fraud score (0–100)\n\n🟢 **0–30:** Auto-approved (Low Risk)\n🟡 **31–60:** Standard review (Medium Risk)\n🔴 **61–100:** Manual investigation (High Risk)\n\nFactors checked: claim patterns, timing, amount vs policy limit, document consistency, and more.",
    "eligibility": "**STP Eligibility Requirements:**\n\n✅ Claim amount under $5,000\n✅ Active policy (not expired)\n✅ No prior fraud flags on account\n✅ Valid claim type (auto, health, travel, property)\n✅ Less than 3 claims in recent period\n\nMeeting all criteria → your claim can be auto-approved in under 5 minutes!",
    "settlement": "**How Settlement is Calculated:**\n\n1. **Base Amount** = Claim Amount - Deductible\n2. **Deductible Rates:** Auto 10%, Health 5%, Travel 8%, Property 12%\n3. **Risk Adjustment:** Medium risk = 5-10% reduction\n4. **Policy Limit Cap:** Cannot exceed your coverage limit\n\nExample: $2,000 auto claim → $200 deductible → $1,800 approved",
}


def _get_fallback_response(message: str) -> str:
    """Rule-based fallback when Gemini is unavailable."""
    lower = message.lower()

    if any(w in lower for w in ["auto", "car", "vehicle", "accident"]):
        return FALLBACK_RESPONSES["auto"]
    elif any(w in lower for w in ["health", "medical", "hospital", "doctor"]):
        return FALLBACK_RESPONSES["health"]
    elif any(w in lower for w in ["travel", "flight", "trip", "cancel"]):
        return FALLBACK_RESPONSES["travel"]
    elif any(w in lower for w in ["property", "home", "house", "damage"]):
        return FALLBACK_RESPONSES["property"]
    elif any(w in lower for w in ["document", "upload", "file", "what do i need"]):
        return FALLBACK_RESPONSES["documents"]
    elif any(w in lower for w in ["fraud", "score", "risk", "flag"]):
        return FALLBACK_RESPONSES["fraud"]
    elif any(w in lower for w in ["eligible", "eligib", "qualify", "stp"]):
        return FALLBACK_RESPONSES["eligibility"]
    elif any(w in lower for w in ["settle", "amount", "pay", "how much", "calculate"]):
        return FALLBACK_RESPONSES["settlement"]
    else:
        return (
            "I'm your ClaimIQ Copilot! I can help with:\n\n"
            "• 📋 **What documents do I need?**\n"
            "• 💰 **How is settlement calculated?**\n"
            "• ⚡ **Am I eligible for auto-approval?**\n"
            "• 🔍 **How does fraud detection work?**\n"
            "• 🚗 **Auto/Health/Travel/Property** claim guidance\n\n"
            "Just ask me anything about your claim!"
        )


async def _get_gemini_response(message: str, claim_type: str = None, claim_amount: float = None) -> str:
    """Get response from Google Gemini API."""
    try:
        import google.generativeai as genai

        if not settings.GEMINI_API_KEY:
            return _get_fallback_response(message)

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        context = f"""You are ClaimIQ Copilot, an AI assistant for an insurance claim processing system.
You help users understand:
- Whether their claim is eligible for auto-approval (STP)
- What documents they need to upload
- How settlement is calculated
- How fraud detection works
- Their approximate approval chances

Key system facts:
- Claims under $5,000 are STP-eligible (auto-approved in <5 minutes)
- Deductible rates: Auto 10%, Health 5%, Travel 8%, Property 12%
- Fraud score 0-30 = auto-approve, 31-60 = manual review, 61-100 = investigation
- 12 fraud rules + ML model analyze each claim
- Required docs: Auto (police report, photos, invoice), Health (hospital bill, prescription, ID), Travel (booking, cancellation proof, passport), Property (photos, invoice, ID)

User's context: {f'Claim type: {claim_type}' if claim_type else 'No claim type specified'}. {f'Amount: ${claim_amount:,.2f}' if claim_amount else 'No amount specified'}.

Keep responses concise (max 150 words), helpful, and professional. Use bullet points and emojis for readability. Do not hallucinate features that don't exist."""

        response = model.generate_content(f"{context}\n\nUser: {message}")
        return response.text

    except ImportError:
        return _get_fallback_response(message)
    except Exception as e:
        print(f"[Copilot] Gemini error: {e}")
        return _get_fallback_response(message)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatMessage,
    current_user: User = Depends(get_current_user),
):
    """AI-powered claim copilot chat endpoint."""
    reply = await _get_gemini_response(
        payload.message,
        payload.claim_type,
        payload.claim_amount,
    )

    # Generate contextual suggestions
    suggestions = _get_suggestions(payload.message)

    return ChatResponse(reply=reply, suggestions=suggestions)


def _get_suggestions(message: str) -> list:
    """Generate follow-up suggestion buttons based on context."""
    lower = message.lower()
    suggestions = []

    if any(w in lower for w in ["auto", "health", "travel", "property"]):
        suggestions = ["What documents do I need?", "Am I eligible for STP?", "Estimate my settlement"]
    elif "document" in lower:
        suggestions = ["Check my eligibility", "How does fraud scoring work?", "Submit my claim"]
    elif "fraud" in lower or "risk" in lower:
        suggestions = ["What can I do to lower risk?", "What documents help?", "Check eligibility"]
    elif "settle" in lower or "amount" in lower:
        suggestions = ["What's the deductible?", "How long does it take?", "Submit my claim"]
    else:
        suggestions = ["Auto claim help", "What documents do I need?", "How does STP work?", "Check eligibility"]

    return suggestions
