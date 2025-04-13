import json
import logging
import re
from openai import OpenAI

logging.basicConfig(filename="logs/discharge_summary.log", level=logging.INFO)

def load_patient_data(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def few_shot_examples():
    return """
Discharge Summary Example

**Patient Information:**  
REDACTED_NAME is a REDACTED_AGE-year-old REDACTED_GENDER admitted on REDACTED_ADMIT_DATE and discharged on REDACTED_DISCHARGE_DATE.

**Diagnosis:**  
Diagnosed with lobar pneumonia, unspecified organism (ICD-10: J18.1).

**Summary of Care:**  
The patient presented with fever, cough, and shortness of breath. Chest X-ray confirmed consolidation in the left lower lobe. Lab tests showed elevated CRP and WBC. Treatment included intravenous Amoxicillin, Paracetamol, and Atorvastatin. Inflammatory markers trended down and the patient improved clinically. Antibiotics were transitioned to oral form by day 3.

**Disposition:**  
At discharge, the patient was afebrile, stable, breathing comfortably, and tolerating oral intake.

**Follow-up Plan:**  
Complete 5 more days of oral antibiotics. A follow-up appointment is scheduled in 2 weeks.

**Contact:**  
For any concerns, contact our clinic.  
Sincerely,  
REDACTED_DOCTOR

---

Discharge Summary Example

**Patient Information:**  
REDACTED_NAME, a REDACTED_AGE-year-old REDACTED_GENDER, was admitted on REDACTED_ADMIT_DATE for neurological evaluation and discharged on REDACTED_DISCHARGE_DATE.

**Diagnosis:**  
Intracerebral hemorrhage, unspecified (ICD-10: I61.9).

**Summary of Care:**  
Imaging confirmed a right hemispheric hemorrhage. The patient received Mannitol for cerebral edema and antihypertensives. Serial neurological exams showed consistent right-sided weakness but no further decline. Family was informed of prognosis and support plans were discussed.

**Disposition:**  
The patient’s vitals remained stable. Discharge planning included safety measures and monitoring. Patient was discharged to home care under close supervision.

**Follow-up Plan:**  
Outpatient neurology follow-up in one week. Repeat CT scan ordered. Family advised on fall precautions and emergency warning signs.

**Contact:**  
Neurology clinic is available for urgent concerns.  
Sincerely,  
REDACTED_DOCTOR
""".strip()

def get_doctor_name(data):
    notes = data.get("notes", [])
    if notes and "author" in notes[-1]:
        return notes[-1]["author"]
    return "REDACTED_DOCTOR"

def generate_prompt(data, few_shot=True):
    diagnosis = ", ".join([d["description"] for d in data.get("diagnoses", [])])
    meds = "\n".join([
        f"{m['medication']} {m['dose']} ({m.get('frequency', 'N/A')})"
        for m in data.get("med_orders", [])
    ])
    notes = "\n".join([
        f"{n.get('date', '')}: {n.get('content', n.get('note', ''))}"
        for n in data.get("notes", []) + data.get("ward_round_notes", [])
    ])

    prompt_body = f"""
Date: REDACTED_DISCHARGE_DATE  
Patient: REDACTED_NAME  
Age: REDACTED_AGE  
Gender: REDACTED_GENDER  
Admission Date: REDACTED_ADMIT_DATE  
Diagnosis: {diagnosis}  

Clinical Notes:  
{notes}  

Medications:  
{meds}  

Please write a detailed discharge summary using the following sections in paragraph form:

- **Patient Information**  
- **Diagnosis**  
- **Summary of Care**  
- **Disposition**  
- **Follow-up Plan**  
- **Contact**

Include:
- Reasoning behind clinical decisions
- Trends in labs/vitals without overlisting
- Recovery status and follow-up expectations

This summary is shared with patients and clinicians. Use clear language. Keep placeholders like REDACTED_NAME unchanged.

Conclude with:  
Sincerely,  
REDACTED_DOCTOR
""".strip()

    if few_shot:
        return few_shot_examples() + "\n\n---\n\n" + prompt_body
    return prompt_body

def get_discharge_summary(data, api_key, few_shot=True, model="gpt-3.5-turbo", additional_instruction=""):
    prompt = generate_prompt(data, few_shot)
    if additional_instruction.strip():
        prompt += f"\n\n# Additional Instruction:\n{additional_instruction.strip()}"
    prompt += "\n\nIMPORTANT: Keep placeholders like REDACTED_NAME and REDACTED_DOCTOR exactly as written."

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )

    result = response.choices[0].message.content

    # Clean placeholder formatting
    placeholders = [
        "REDACTED_NAME", "REDACTED_AGE", "REDACTED_GENDER",
        "REDACTED_ADMIT_DATE", "REDACTED_DISCHARGE_DATE", "REDACTED_DOCTOR"
    ]
    for ph in placeholders:
        result = re.sub(rf'([a-zA-Z]){ph}', r'\1 ' + ph, result)
        result = re.sub(rf'{ph}([a-zA-Z])', ph + r' \1', result)

    return result

def extract_highlights(summary_text, api_key, model="gpt-4"):
    prompt = f"""
From the discharge summary below, extract a JSON list of important clinical highlights. 
Each item should include a "text" field with the exact phrase and a "category" field from this set:
["diagnosis", "duration", "medication", "investigation_result", "lab_result", "clinical_trend", "recovery_status", "discharge_criteria", "followup_action", "followup_timing", "red_flag_instruction", "patient_info"]

Return ONLY valid JSON like:
[
  {{ "text": "5 more days", "category": "duration" }},
  {{ "text": "diagnosed with lobar pneumonia", "category": "diagnosis" }}
]

SUMMARY:
{summary_text}
"""

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Highlight JSON parse failed: {e}")
        return []

def validate_discharge_safety(summary_text, api_key, model="gpt-4"):
    prompt = f"""
Evaluate this discharge summary and determine if the patient is medically safe to discharge. 
Return one of: "Yes", "No", or "Uncertain", followed by a brief explanation.

SUMMARY:
{summary_text}
"""

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content.strip()
