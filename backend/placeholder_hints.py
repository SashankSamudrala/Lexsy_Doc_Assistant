# backend/placeholder_hints.py
import re

# If your editor complains about the relative import above, ignore — app.py will import generate_hint directly from this file.
# We do not actually need normalize_key here, simple string checks suffice.

def generate_hint(key: str) -> str:
    """
    Heuristic hints to give the LLM semantic context for each placeholder.
    Keep this deterministic and conservative.
    """
    k = key.strip().strip("[]").lower()

    # Money
    if any(w in k for w in ["purchase amount", "purchase price", "price", "amount", "consideration", "principal", "valuation cap", "cap"]):
        if "valuation" in k or "cap" in k:
            return "Maximum valuation used to compute conversion; a dollar amount"
        if "principal" in k:
            return "Principal money amount agreed in the instrument"
        if "purchase price" in k or "purchase amount" in k or "price" in k:
            return "Amount of money to be paid by the buyer or investor"
        return "Dollar amount relevant to the agreement"

    # Company / Party names
    if any(w in k for w in ["company", "corporation", "issuer", "startup", "entity name"]):
        return "Legal name of the issuing company"

    if any(w in k for w in ["investor", "purchaser", "buyer", "lender", "holder"]):
        return "Legal name of the investor or purchaser"

    if "name" in k and "company" not in k and "investor" not in k:
        return "Personal full name"

    if "title" in k:
        return "Person's title or role (e.g., CEO, CFO)"

    # Jurisdiction / location
    if any(w in k for w in ["state", "jurisdiction", "governing law", "governing", "country"]):
        return "Governing law or state/country of incorporation"

    # Date
    if "date" in k:
        return "Calendar date of the event in Month D, YYYY format"

    # Generic text
    return "Relevant value for this placeholder as it appears in the document"
