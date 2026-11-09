"""
Financial & Invoice Intelligence Tool
Extracts structured invoice and receipt data (vendor, invoice #, line items, totals, dates)
for accounting and enterprise AI agents.
"""
import io
import re
import os
import time
import base64
import httpx
from typing import Optional, List, Dict, Any, Tuple
from pypdf import PdfReader
from app.models import (
    InvoiceExtractRequest,
    InvoiceExtractResponse,
    InvoiceData,
    InvoiceLineItem,
)


def _clean_amount(text: str) -> Optional[float]:
    """Clean monetary strings like '$ 1,234.50' into float 1234.50"""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.-]", "", text.replace(",", ""))
    try:
        val = float(cleaned)
        return round(val, 2)
    except ValueError:
        return None


def _detect_currency(text: str, default: str = "USD") -> str:
    """Detect currency symbol or code from document text."""
    currency_map = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "USD": "USD",
        "EUR": "EUR",
        "GBP": "GBP",
        "CAD": "CAD",
        "AUD": "AUD",
        "INR": "INR",
    }
    for symbol, code in currency_map.items():
        if symbol in text:
            return code
    return default


def _extract_patterns(text: str, currency_hint: str = "USD") -> Tuple[InvoiceData, float, bool]:
    """
    Deterministic rule-based extraction engine.
    Runs locally on-server at zero cost with high reliability.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    full_text_lower = text.lower()

    # 1. Document Type
    doc_type = "invoice"
    if "receipt" in full_text_lower:
        doc_type = "receipt"
    elif "statement" in full_text_lower:
        doc_type = "statement"
    elif "purchase order" in full_text_lower:
        doc_type = "purchase_order"
    elif "credit note" in full_text_lower:
        doc_type = "credit_note"

    # 2. Currency
    currency = _detect_currency(text, default=currency_hint)

    # 3. Invoice Number
    inv_num = None
    inv_match = re.search(
        r"(?:invoice\s*(?:number|num|no|#)|inv\s*(?:number|num|no|#)|receipt\s*(?:number|num|no|#)|bill\s*#|invoice\s*id)[:.\s#]+([A-Za-z0-9-_/]{3,30})",
        text,
        re.IGNORECASE,
    )
    if inv_match:
        val = inv_match.group(1).strip()
        if not re.search(r"date|total|amount|due|usd|eur|number", val, re.I):
            inv_num = val

    # 4. PO Number
    po_num = None
    po_match = re.search(
        r"(?:p\.?o\.?\s*(?:number|num|no|#)|purchase\s*order\s*(?:number|num|no|#)|p\.?o\.?)[:.\s#]+([A-Za-z0-9-_/]{3,30})",
        text,
        re.IGNORECASE,
    )
    if po_match:
        po_val = po_match.group(1).strip()
        if not re.search(r"date|total|amount|due|number", po_val, re.I):
            po_num = po_val

    # 5. Dates
    inv_date = None
    date_pattern = r"([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})"
    
    date_match = re.search(
        rf"(?:invoice\s*date|issue\s*date|date|dated|billed)[:.\s]*{date_pattern}",
        text,
        re.IGNORECASE,
    )
    if date_match:
        inv_date = date_match.group(1).strip()
    else:
        fallback_date = re.search(date_pattern, text)
        if fallback_date:
            inv_date = fallback_date.group(1).strip()

    due_date = None
    due_match = re.search(
        rf"(?:due\s*date|payment\s*due|pay\s*by)[:.\s]*{date_pattern}",
        text,
        re.IGNORECASE,
    )
    if due_match:
        due_date = due_match.group(1).strip()

    # 6. Vendor & Customer Extraction
    vendor_name = "Unknown Vendor"
    customer_name = None

    cust_match = re.search(
        r"(?:bill\s*to|billed\s*to|sold\s*to|customer|client|invoice\s*to)[:\s]*\n?([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if cust_match:
        customer_name = cust_match.group(1).strip()

    for line in lines[:5]:
        if not re.search(r"invoice|receipt|tax|bill|date|#|page|po\s*number", line, re.I) and len(line) > 2:
            vendor_name = line
            break

    # 7. Tax ID / VAT
    tax_id = None
    tax_id_match = re.search(
        r"(?:vat|tax\s*id|gst|ein|tin|abn|rfc)[:.\s]*([A-Za-z0-9-_]{5,20})",
        text,
        re.IGNORECASE,
    )
    if tax_id_match:
        tax_id = tax_id_match.group(1).strip()

    # 8. Totals (Subtotal, Tax, Total)
    total_amount = 0.0
    subtotal = None
    tax_amount = None

    subtotal_match = re.search(
        r"(?:subtotal|sub-total|net\s*amount)\s*[:\s]*[$€£]?\s*([0-9,]+\.[0-9]{2})",
        text,
        re.IGNORECASE,
    )
    if subtotal_match:
        subtotal = _clean_amount(subtotal_match.group(1))

    tax_match = re.search(
        r"(?:tax|vat|gst|sales\s*tax)\s*(?:\([0-9.]+%\))?\s*[:\s]*[$€£]?\s*([0-9,]+\.[0-9]{2})",
        text,
        re.IGNORECASE,
    )
    if tax_match:
        tax_amount = _clean_amount(tax_match.group(1))

    total_match = re.search(
        r"(?<!sub)(?:total|amount\s*due|balance\s*due|grand\s*total)\s*(?:due)?[:\s]*[$€£]?\s*([0-9,]+\.[0-9]{2})",
        text,
        re.IGNORECASE,
    )
    if total_match:
        total_amount = _clean_amount(total_match.group(1)) or 0.0

    # 9. Line Items Extraction
    line_items: List[InvoiceLineItem] = []
    line_item_pattern = re.compile(
        r"^(.+?)\s+([0-9]+(?:\.[0-9]+)?)\s+[$€£]?\s*([0-9,]+\.[0-9]{2})\s+[$€£]?\s*([0-9,]+\.[0-9]{2})$"
    )
    simple_item_pattern = re.compile(
        r"^([A-Za-z0-9\s\-_/,.]{3,50})\s+[$€£]?\s*([0-9,]+\.[0-9]{2})$"
    )

    for line in lines:
        if re.search(r"total|subtotal|balance|tax|vat|date|invoice|page|amount\s*due", line, re.I):
            continue
        
        m = line_item_pattern.match(line)
        if m:
            desc = m.group(1).strip()
            qty = float(m.group(2))
            unit_p = _clean_amount(m.group(3))
            tot_p = _clean_amount(m.group(4)) or 0.0
            line_items.append(
                InvoiceLineItem(description=desc, quantity=qty, unit_price=unit_p, total_price=tot_p)
            )
        else:
            sm = simple_item_pattern.match(line)
            if sm:
                desc = sm.group(1).strip()
                tot_p = _clean_amount(sm.group(2)) or 0.0
                if tot_p > 0:
                    line_items.append(
                        InvoiceLineItem(description=desc, quantity=1.0, unit_price=tot_p, total_price=tot_p)
                    )

    # 10. Math Verification & Confidence Scoring
    math_verified = False
    if subtotal is not None and tax_amount is not None and total_amount > 0:
        expected = subtotal + tax_amount
        math_verified = abs(expected - total_amount) < 0.05
    elif subtotal is not None and total_amount > 0:
        math_verified = abs(subtotal - total_amount) < 0.05

    # Compute confidence
    score = 0.2
    if total_amount > 0: score += 0.25
    if inv_num: score += 0.20
    if inv_date: score += 0.15
    if vendor_name != "Unknown Vendor": score += 0.1
    if line_items: score += 0.1
    if math_verified: score += 0.1
    confidence_score = round(min(1.0, score), 2)

    invoice_data = InvoiceData(
        document_type=doc_type,
        invoice_number=inv_num,
        purchase_order=po_num,
        vendor_name=vendor_name,
        vendor_tax_id=tax_id,
        customer_name=customer_name,
        invoice_date=inv_date,
        due_date=due_date,
        currency=currency,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        line_items=line_items,
    )

    return invoice_data, confidence_score, math_verified


async def extract_invoice(request: InvoiceExtractRequest) -> InvoiceExtractResponse:
    """
    Process invoice/receipt from URL, Base64, or Raw Text.
    """
    start_time = time.time()
    extracted_text = ""

    if request.raw_text:
        extracted_text = request.raw_text
    else:
        file_bytes: bytes = b""
        if request.url:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgentToolsInvoiceBot/1.0"
                )
            }
            async with httpx.AsyncClient(follow_redirects=True, timeout=25.0, headers=headers) as client:
                resp = await client.get(str(request.url))
                resp.raise_for_status()
                file_bytes = resp.content
        elif request.file_base64:
            try:
                file_bytes = base64.b64decode(request.file_base64)
            except Exception as e:
                raise ValueError(f"Invalid base64 payload: {str(e)}")
        else:
            raise ValueError("Provide 'url', 'file_base64', or 'raw_text'.")

        # Check if PDF or Image
        is_pdf = file_bytes[:4] == b"%PDF"
        if is_pdf:
            stream = io.BytesIO(file_bytes)
            reader = PdfReader(stream)
            page_texts = [page.extract_text() or "" for page in reader.pages[:10]]
            extracted_text = "\n".join(page_texts)
        else:
            try:
                extracted_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = "Binary file received."

    invoice_data, confidence, math_verified = _extract_patterns(
        extracted_text, currency_hint=request.currency_hint or "USD"
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return InvoiceExtractResponse(
        success=True,
        invoice=invoice_data,
        confidence_score=confidence,
        math_verified=math_verified,
        processing_time_ms=elapsed_ms,
        method_used="deterministic_layout_engine",
    )
