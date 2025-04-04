import json
import re
import unicodedata
import copy

def normalize_text(text):
    """Normalize text to remove zero-width and non-breaking spaces."""
    return unicodedata.normalize("NFKC", text).replace("\u200b", "").replace("\xa0", " ")

def redact_pii(data):
    redacted = copy.deepcopy(data)  # ✅ Full deep copy to preserve original

    if "patient_demographics" in redacted:
        redacted["patient_demographics"]["name"] = "REDACTED_NAME"
        redacted["patient_demographics"]["dob"] = "REDACTED_DOB"
        redacted["patient_demographics"]["admission_date"] = "REDACTED_ADMIT_DATE"
        redacted["patient_demographics"]["discharge_date"] = "REDACTED_DISCHARGE_DATE"
        redacted["patient_demographics"]["gender"] = redacted["patient_demographics"].get("gender", "REDACTED_GENDER")
        redacted["patient_demographics"]["age"] = "REDACTED_AGE"

    redacted["patient_id"] = "REDACTED_ID"

    if "notes" in redacted and redacted["notes"]:
        redacted["notes"][-1]["author"] = "REDACTED_DOCTOR"

    return redacted

def insert_pii(text, data):
    """
    Replace redacted placeholders with actual patient information.
    Handles exact matches and mangled (spaced) versions.
    """
    text = normalize_text(text)

    demo = data.get("patient_demographics", {})
    notes = data.get("notes", [])
    doctor = notes[-1]["author"] if notes and "author" in notes[-1] else "The Discharging Physician"

    replacements = {
        "REDACTED_NAME": demo.get("name", "the patient"),
        "REDACTED_AGE": str(demo.get("age", "Unknown age")),
        "REDACTED_GENDER": demo.get("gender", "Unknown"),
        "REDACTED_ADMIT_DATE": demo.get("admission_date", "N/A"),
        "REDACTED_DISCHARGE_DATE": demo.get("discharge_date", "N/A"),
        "REDACTED_ID": str(data.get("patient_id", "--")),
        "REDACTED_DOCTOR": doctor,
    }

    for placeholder, real_val in replacements.items():
        # Replace normal placeholder (no word boundaries so it catches e.g., REDACTED_NAME,)
        text = re.sub(re.escape(placeholder), real_val, text)

        # Replace broken/spaced-out placeholder e.g., R E D A C T E D _ D O C T O R
        spaced_pattern = r'\s*'.join(list(placeholder))
        text = re.sub(spaced_pattern, real_val, text, flags=re.IGNORECASE)

    return text

def is_safe_for_discharge(data):
    """
    Check if discharge is medically safe by looking for red flag terms in notes.
    """
    notes = json.dumps(data.get("notes", []) + data.get("ward_round_notes", [])).lower()
    red_flags = ["not safe for discharge", "critical", "unstable", "requires monitoring"]
    return not any(flag in notes for flag in red_flags)

def passes_specificity_check(text):
    """
    Very basic keyword-based check to flag potential lack of follow-up or detail.
    """
    required_terms = ["follow-up", "mg", "clinic"]
    return all(term in text.lower() for term in required_terms)
