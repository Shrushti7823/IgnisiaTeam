"""
ClaimIQ - Sample Claim PDF Generator
======================================
Generates two sample claim PDFs for demonstrating the system:
  1. sample_claim_approved.pdf  — Clean, legitimate claim → STP auto-approval
  2. sample_claim_rejected.pdf  — Suspicious claim with fraud indicators → rejection

Run: python scripts/generate_sample_pdfs.py
Output: sample_claims/ directory
"""

import os
import sys
from datetime import datetime, timedelta

# We use reportlab if available, otherwise create simple PDF manually
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_claims")


def create_pdf_with_reportlab(filename: str, content: dict):
    """Generate a professional PDF using reportlab."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=6,
        textColor=colors.HexColor('#1e3a5f'),
        fontName='Helvetica-Bold',
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20,
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        spaceAfter=8,
        spaceBefore=16,
        textColor=colors.HexColor('#1e3a5f'),
        fontName='Helvetica-Bold',
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
        textColor=colors.HexColor('#374151'),
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER,
    )
    
    elements = []
    
    # ── Header ──
    header_data = [
        [
            Paragraph(f"<b>{content['company_name']}</b>", ParagraphStyle('BrandName', parent=styles['Normal'], fontSize=16, textColor=colors.HexColor('#4f46e5'), fontName='Helvetica-Bold')),
            Paragraph(f"<b>{content['doc_title']}</b>", ParagraphStyle('DocTitle', parent=styles['Normal'], fontSize=11, alignment=TA_RIGHT, textColor=colors.HexColor('#6b7280'))),
        ],
        [
            Paragraph(content['company_address'], ParagraphStyle('Addr', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#9ca3af'))),
            Paragraph(f"Date: {content['date']}", ParagraphStyle('Date', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT, textColor=colors.HexColor('#6b7280'))),
        ],
    ]
    header_table = Table(header_data, colWidths=[300, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#4f46e5'), spaceAfter=12))
    
    # ── Document Reference ──
    ref_data = [
        ['Document Reference:', content['reference']],
        ['Document Type:', content['doc_type']],
        ['Claimant Name:', content['claimant_name']],
        ['Policy Number:', content['policy_number']],
    ]
    ref_table = Table(ref_data, colWidths=[140, 360])
    ref_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1f2937')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(ref_table)
    elements.append(Spacer(1, 16))
    
    # ── Sections ──
    for section in content['sections']:
        elements.append(Paragraph(section['title'], heading_style))
        
        if 'text' in section:
            elements.append(Paragraph(section['text'], body_style))
        
        if 'table' in section:
            tdata = section['table']
            t = Table(tdata, colWidths=section.get('col_widths', None))
            style_cmds = [
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef2ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4338ca')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#c7d2fe')),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ]
            t.setStyle(TableStyle(style_cmds))
            elements.append(t)
            elements.append(Spacer(1, 8))
        
        if 'items' in section:
            for item in section['items']:
                elements.append(Paragraph(f"• {item}", body_style))
    
    # ── Verification / Stamp ──
    if 'stamp' in content:
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=12))
        stamp_style = ParagraphStyle(
            'Stamp',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#059669'),
            fontName='Helvetica-Bold',
        )
        elements.append(Paragraph(content['stamp'], stamp_style))
    
    # ── Footer ──
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
    elements.append(Paragraph(content.get('footer', 'This document is system-generated and may be used for insurance claim processing.'), footer_style))
    
    doc.build(elements)
    return filepath


def create_simple_pdf(filename: str, lines: list):
    """Fallback: create a minimal valid PDF without reportlab."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Build a minimal PDF manually
    text_content = "\n".join(lines)
    stream = text_content.encode('latin-1', errors='replace')
    
    objects = []
    
    # Object 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    # Object 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    
    # Object 3: Page
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    
    # Object 4: Content stream
    pdf_lines = []
    y = 800
    for line in lines:
        safe = line.replace('(', '\\(').replace(')', '\\)')
        if line.startswith('===') or line.startswith('---'):
            continue
        if line.startswith('# '):
            pdf_lines.append(f"BT /F1 16 Tf 50 {y} Td ({safe[2:]}) Tj ET")
            y -= 24
        elif line.startswith('## '):
            pdf_lines.append(f"BT /F1 12 Tf 50 {y} Td ({safe[3:]}) Tj ET")
            y -= 20
        elif line.strip():
            pdf_lines.append(f"BT /F1 9 Tf 50 {y} Td ({safe}) Tj ET")
            y -= 14
        else:
            y -= 10
        if y < 50:
            break
    
    stream_content = "\n".join(pdf_lines).encode('latin-1', errors='replace')
    stream_obj = f"4 0 obj\n<< /Length {len(stream_content)} >>\nstream\n".encode() + stream_content + b"\nendstream\nendobj\n"
    objects.append(stream_obj)
    
    # Object 5: Font
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    # Build PDF
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj
    
    xref_start = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    
    pdf += b"trailer\n"
    pdf += f"<< /Root 1 0 R /Size {len(objects) + 1} >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_start}\n".encode()
    pdf += b"%%EOF\n"
    
    with open(filepath, 'wb') as f:
        f.write(pdf)
    
    return filepath


# ════════════════════════════════════════════════════════════════════
# CONTENT DEFINITIONS
# ════════════════════════════════════════════════════════════════════

today = datetime.now()
incident_date_clean = (today - timedelta(days=3)).strftime("%B %d, %Y")
incident_date_suspicious = (today - timedelta(days=45)).strftime("%B %d, %Y")

# ── PDF 1: CLEAN CLAIM (Auto-Approval) ──
CLEAN_CLAIM = {
    "company_name": "AutoCare Service Center",
    "company_address": "4521 Oak Valley Road, Suite 12, Austin, TX 78701 | Tel: (512) 555-0147 | License: TX-ASC-88421",
    "doc_title": "VEHICLE REPAIR INVOICE",
    "date": today.strftime("%B %d, %Y"),
    "reference": "INV-2026-04871",
    "doc_type": "Invoice / Repair Bill",
    "claimant_name": "John M. Davis",
    "policy_number": "POL-2026-001",
    "stamp": "✓ VERIFIED — AutoCare Service Center (Licensed TX Automotive Repair Facility)",
    "footer": "AutoCare Service Center — Certified Automotive Repair since 2008. All work guaranteed 12 months / 12,000 miles.",
    "sections": [
        {
            "title": "Incident Details",
            "text": f"On <b>{incident_date_clean}</b>, the insured vehicle (2021 Honda Civic, VIN: 1HGBH41JXMN109186) "
                    "sustained damage to the front bumper and headlight assembly following a minor parking lot collision "
                    "at HEB Grocery, 1205 Barton Springs Rd, Austin TX. No injuries reported. Police report filed "
                    "(APD Case #2026-PL-04521).",
        },
        {
            "title": "Itemized Repair Costs",
            "table": [
                ["Item", "Description", "Parts ($)", "Labor ($)", "Total ($)"],
                ["1", "Front bumper cover — OEM Honda replacement", "385.00", "120.00", "505.00"],
                ["2", "Left headlight assembly — OEM replacement", "210.00", "85.00", "295.00"],
                ["3", "Bumper reinforcement bar — inspection & realignment", "—", "95.00", "95.00"],
                ["4", "Paint match & blend — front bumper (3-stage)", "65.00", "180.00", "245.00"],
                ["5", "Diagnostic scan — pre/post repair verification", "—", "60.00", "60.00"],
                ["", "", "", "Subtotal", "$1,200.00"],
            ],
            "col_widths": [30, 230, 65, 65, 70],
        },
        {
            "title": "Payment Summary",
            "table": [
                ["Description", "Amount"],
                ["Repair Subtotal", "$1,200.00"],
                ["Sales Tax (8.25%)", "$0.00 (insurance exempt)"],
                ["Total Due", "$1,200.00"],
                ["Insurance Claim Amount", "$1,200.00"],
            ],
            "col_widths": [300, 200],
        },
        {
            "title": "Vehicle Information",
            "table": [
                ["Field", "Details"],
                ["Year / Make / Model", "2021 Honda Civic LX"],
                ["VIN", "1HGBH41JXMN109186"],
                ["License Plate", "TX LBK-4827"],
                ["Odometer (at repair)", "34,218 miles"],
                ["Color", "Aegean Blue Metallic"],
            ],
            "col_widths": [150, 350],
        },
        {
            "title": "Technician Certification",
            "text": "I certify that all repairs listed above have been completed using OEM-specification parts. "
                    "The vehicle has been inspected and is safe to operate. All work is covered by our 12-month warranty.<br/><br/>"
                    "<b>Lead Technician:</b> Robert M. Chen, ASE Certified Master Technician #TX-44218<br/>"
                    "<b>Shop Manager:</b> Maria L. Gonzalez<br/>"
                    "<b>Date of Completion:</b> " + today.strftime("%B %d, %Y"),
        },
    ],
}


# ── PDF 2: SUSPICIOUS CLAIM (Fraud/Rejection) ──
SUSPICIOUS_CLAIM = {
    "company_name": "Global Medical Associates",
    "company_address": "Suite 5, Medical Plaza, 999 Health Blvd, Somewhere, FL 00000 | Tel: (000) 555-9999",
    "doc_title": "MEDICAL TREATMENT INVOICE",
    "date": today.strftime("%B %d, %Y"),
    "reference": "MED-2026-99000",
    "doc_type": "Medical Bill",
    "claimant_name": "Amit R. Suspicious",
    "policy_number": "POL-2026-003",
    "stamp": "",  # No verification stamp — suspicious
    "footer": "Global Medical Associates — General Practice.",
    "sections": [
        {
            "title": "Patient Treatment Summary",
            "text": f"Patient presented on <b>{incident_date_suspicious}</b> complaining of severe back pain following "
                    "an alleged workplace incident. Treatment was provided over a single visit with extensive diagnostic "
                    "procedures. <i>Note: Patient insisted on maximum treatment scope. Incident date was over 40 days ago "
                    "but patient only sought treatment now.</i>",
        },
        {
            "title": "Itemized Treatment Costs",
            "text": "<b><font color='red'>⚠ MULTIPLE FRAUD INDICATORS PRESENT IN THIS DOCUMENT</font></b>",
        },
        {
            "title": "Billing Details",
            "table": [
                ["Item", "Description", "Amount ($)"],
                ["1", "Full spinal MRI scan — comprehensive", "1,500.00"],
                ["2", "Physical therapy session (x4) — intensive", "800.00"],
                ["3", "Prescription medications — assorted", "500.00"],
                ["4", "Specialist consultation fee — orthopedic", "1,000.00"],
                ["5", "Follow-up visit scheduling fee", "500.00"],
                ["6", "Administrative processing surcharge", "500.00"],
                ["", "", ""],
                ["", "TOTAL AMOUNT CLAIMED", "$4,800.00"],
            ],
            "col_widths": [30, 350, 100],
        },
        {
            "title": "⚠ Red Flags for AI Fraud Detection",
            "items": [
                "<b>Late Reporting (45 days)</b> — Treatment sought 45 days after alleged incident (threshold: 30 days)",
                "<b>Near Policy Limit</b> — $4,800 claim on $5,000 policy = 96% of limit (trigger: ≥90%)",
                "<b>Round Numbers</b> — All line items are suspiciously round ($500, $1,000, $1,500)",
                "<b>Excessive Charges</b> — $500 'administrative processing surcharge' is unusual",
                "<b>Generic Provider</b> — 'Global Medical Associates' with address '999 Health Blvd, Somewhere, FL 00000'",
                "<b>No Provider License</b> — Document lacks any medical license number or NPI",
                "<b>Prior Fraud Flags</b> — This policyholder account has 2 prior fraud flags on record",
                "<b>High Claim Frequency</b> — This is the 3rd claim filed in the past 90 days",
                "<b>Date Mismatch</b> — Incident date vs treatment date inconsistency (45 day gap)",
                "<b>Missing Verification</b> — No doctor's signature, stamp, or NPI number present",
            ],
        },
        {
            "title": "Expected System Behavior",
            "text": "When this document is submitted through the ClaimIQ system, the following should occur:<br/><br/>"
                    "1. <b>Gate 1 (Eligibility)</b>: May fail due to prior fraud flags<br/>"
                    "2. <b>Gate 2 (Document Verification)</b>: OCR will flag missing provider credentials<br/>"
                    "3. <b>Gate 3 (Fraud Engine)</b>: Multiple soft rules triggered — late reporting, round numbers, "
                    "high amount/limit ratio, prior fraud history, claim frequency<br/>"
                    "4. <b>Gate 4 (Risk Scoring)</b>: Risk score will be very high (80+)<br/>"
                    "5. <b>Gate 5 (Decision)</b>: Auto-rejected or sent to manual review queue<br/><br/>"
                    "<b>Expected Fraud Score: 75–95 out of 100</b><br/>"
                    "<b>Expected Decision: REJECTED or MANUAL_REVIEW</b>",
        },
        {
            "title": "Disclaimer",
            "text": "<i>This is a SAMPLE document created for ClaimIQ system demonstration purposes. "
                    "It intentionally contains fraud indicators to test the system's detection capabilities. "
                    "No actual medical services were rendered.</i>",
        },
    ],
}


# ── SIMPLE TEXT VERSIONS (fallback) ──
CLEAN_TEXT = [
    "# VEHICLE REPAIR INVOICE",
    "## AutoCare Service Center",
    "4521 Oak Valley Road, Suite 12, Austin, TX 78701",
    "License: TX-ASC-88421 | Tel: (512) 555-0147",
    "",
    f"Date: {today.strftime('%B %d, %Y')}",
    "Reference: INV-2026-04871",
    "Claimant: John M. Davis",
    "Policy: POL-2026-001",
    "",
    "## Incident Details",
    f"On {incident_date_clean}, the insured vehicle (2021 Honda Civic,",
    "VIN: 1HGBH41JXMN109186) sustained front bumper and headlight",
    "damage in a parking lot collision. Police report: APD #2026-PL-04521.",
    "",
    "## Itemized Repairs",
    "1. Front bumper cover (OEM Honda)       $505.00",
    "2. Left headlight assembly (OEM)         $295.00",
    "3. Bumper reinforcement realignment       $95.00",
    "4. Paint match & blend (3-stage)         $245.00",
    "5. Diagnostic scan (pre/post)             $60.00",
    "                                  ──────────────",
    "   TOTAL                              $1,200.00",
    "",
    "## Vehicle Info",
    "2021 Honda Civic LX | VIN: 1HGBH41JXMN109186",
    "License: TX LBK-4827 | Odometer: 34,218 mi",
    "",
    "## Certification",
    "All repairs completed with OEM parts.",
    "Lead Tech: Robert M. Chen, ASE #TX-44218",
    "VERIFIED - Licensed TX Automotive Repair Facility",
]

SUSPICIOUS_TEXT = [
    "# MEDICAL TREATMENT INVOICE",
    "## Global Medical Associates",
    "Suite 5, 999 Health Blvd, Somewhere, FL 00000",
    "Tel: (000) 555-9999",
    "",
    f"Date: {today.strftime('%B %d, %Y')}",
    "Reference: MED-2026-99000",
    "Patient: Amit R. Suspicious",
    "Policy: POL-2026-003",
    "",
    "## Treatment Summary",
    f"Patient presented {incident_date_suspicious} with severe back",
    "pain from workplace incident. Treatment 45 days after incident.",
    "Patient insisted on maximum treatment scope.",
    "",
    "## Billing",
    "1. Full spinal MRI scan              $1,500.00",
    "2. Physical therapy (x4)               $800.00",
    "3. Prescription medications            $500.00",
    "4. Specialist consultation           $1,000.00",
    "5. Follow-up scheduling fee            $500.00",
    "6. Admin processing surcharge          $500.00",
    "                              ────────────────",
    "   TOTAL CLAIMED                    $4,800.00",
    "",
    "## FRAUD INDICATORS",
    "- Late reporting: 45 days (threshold 30)",
    "- Near policy limit: 96% ($4,800/$5,000)",
    "- All round numbers ($500, $1,000, $1,500)",
    "- Unusual admin surcharge ($500)",
    "- Generic provider address (Somewhere, FL 00000)",
    "- No medical license or NPI number",
    "- 2 prior fraud flags on account",
    "- 3rd claim in 90 days",
    "- No doctor signature or stamp",
    "",
    "## Expected: FRAUD SCORE 75-95, REJECTED",
    "",
    "SAMPLE DOCUMENT FOR CLAIMIQ DEMO ONLY",
]


def main():
    print("=" * 60)
    print("ClaimIQ — Sample Claim PDF Generator")
    print("=" * 60)
    
    if HAS_REPORTLAB:
        print("\n✅ reportlab found — generating professional PDFs\n")
        
        path1 = create_pdf_with_reportlab("sample_claim_approved.pdf", CLEAN_CLAIM)
        print(f"  ✅ Created: {path1}")
        print(f"     → Clean auto claim, $1,200, legitimate repair invoice")
        print(f"     → Expected: Low fraud score, STP auto-approval\n")
        
        path2 = create_pdf_with_reportlab("sample_claim_rejected.pdf", SUSPICIOUS_CLAIM)
        print(f"  ✅ Created: {path2}")
        print(f"     → Suspicious health claim, $4,800, multiple red flags")
        print(f"     → Expected: High fraud score (75-95), rejection\n")
    else:
        print("\n⚠️  reportlab not found — generating basic PDFs")
        print("   Install with: pip install reportlab\n")
        
        path1 = create_simple_pdf("sample_claim_approved.pdf", CLEAN_TEXT)
        print(f"  ✅ Created: {path1}")
        
        path2 = create_simple_pdf("sample_claim_rejected.pdf", SUSPICIOUS_TEXT)
        print(f"  ✅ Created: {path2}")
    
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    print(f"   Files ready to upload through the ClaimIQ portal.\n")
    
    print("─" * 60)
    print("USAGE INSTRUCTIONS:")
    print("─" * 60)
    print("""
  APPROVAL DEMO (sample_claim_approved.pdf):
    1. Login as: john@demo.com / Demo@123
    2. Submit Claim → Type: Auto, Amount: $1,200
    3. Upload this PDF as 'Invoice'
    4. Submit for processing
    5. Expected: Fraud Score ~8-15, AUTO-APPROVED ✅

  REJECTION DEMO (sample_claim_rejected.pdf):
    1. Login as: amit@demo.com / Demo@123
    2. Submit Claim → Type: Health, Amount: $4,800
    3. Upload this PDF as 'Medical Bill'
    4. Submit for processing
    5. Expected: Fraud Score ~75-95, REJECTED ❌

  ADMIN VIEW:
    1. Login as admin: admin@claimiq.com / Admin@123
    2. Dashboard → See both claims with different outcomes
    3. Fraud Alerts → See triggered rules
    4. Manual Queue → See flagged claims for review
    5. Audit Logs → Full pipeline trace
""")


if __name__ == "__main__":
    main()
