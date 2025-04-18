import copy

def is_safe_for_discharge(data, recent_limit=2):
    """
    Checks only the most recent N notes for discharge-blocking phrases.
    This prevents false negatives if patient status improved later.
    """
    discharge_warning_phrases = [
        "not safe for discharge",
        "condition remains critical",
        "requires close monitoring",
        "unfit for discharge",
        "not medically stable",
    ]

    all_notes = data.get("notes", []) + data.get("ward_round_notes", [])
    # Sort by date (descending) and get the most recent N notes
    recent_notes = sorted(
        all_notes,
        key=lambda x: x.get("date", "") + x.get("time", ""),
        reverse=True
    )[:recent_limit]

    for note in recent_notes:
        content = note.get("content") or note.get("note", "")
        for phrase in discharge_warning_phrases:
            if phrase in content.lower():
                return False
    return True

def redact_pii(data):
    """Redacts PII from patient data before sending to LLM."""
    redacted = copy.deepcopy(data)

    # Redact patient info
    if "patient" in redacted:
        redacted["patient_demographics"]["name"] = "REDACTED_NAME"
        redacted["patient_demographics"]["gender"] = "REDACTED_GENDER"
        redacted["patient_demographics"]["age"] = "REDACTED_AGE"

    # Redact note authors
    for note in redacted.get("notes", []):
        if "author" in note:
            note["author"] = "REDACTED_DOCTOR"

    for note in redacted.get("ward_round_notes", []):
        if "author" in note:
            note["author"] = "REDACTED_DOCTOR"

    return redacted

def insert_pii(text, data):
    """Replaces placeholders with actual patient information (for personal mode display)."""
    patient = data.get("patient_demographics", {})
    replacements = {
        "REDACTED_NAME": patient.get("name", ""),
        "REDACTED_GENDER": patient.get("gender", ""),
        "REDACTED_AGE": str(patient.get("age", "")),
        "REDACTED_ADMIT_DATE": data.get("admit_date", ""),
        "REDACTED_DISCHARGE_DATE": data.get("discharge_date", ""),
        "REDACTED_DOCTOR": get_doctor_name(data),
    }

    for placeholder, actual in replacements.items():
        text = text.replace(placeholder, actual)
    return text

def get_doctor_name(data):
    notes = data.get("notes", []) + data.get("ward_round_notes", [])
    for note in reversed(notes):
        if "author" in note and note["author"].strip():
            return note["author"]
    return "Discharging Doctor"
