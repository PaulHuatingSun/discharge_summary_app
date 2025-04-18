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
Discharge Summary Example (with Chain-of-Thought Reasoning)

**Patient Information:**  
REDACTED_NAME is a REDACTED_AGE-year-old REDACTED_GENDER admitted on 2024-01-05 and discharged on 2024-01-10.

**Diagnosis:**  
Lobar pneumonia, unspecified organism (ICD-10: J18.1)

**Summary of Care:**  
The patient presented with fever, productive cough, and shortness of breath.  
→ A chest X-ray showed left lower lobe consolidation, confirming pneumonia.  
→ Blood tests revealed elevated WBC and CRP, consistent with bacterial infection.  
→ IV Amoxicillin and Paracetamol were started for infection and fever control.  
→ Over 48 hours, the patient's symptoms improved significantly and vitals stabilized.  
→ Antibiotics were transitioned to oral form by Day 3 due to clinical stability.

**Disposition:**  
→ At discharge, the patient was afebrile for more than 48 hours, breathing normally, and tolerating oral intake.  
→ The patient was considered medically stable and discharged with instructions.

**Follow-up Plan:**  
→ Complete oral antibiotics for 5 more days.  
→ Follow-up scheduled in 2 weeks.

**Contact:**  
For concerns, contact the clinic.  
Sincerely,  
REDACTED_DOCTOR

---

Discharge Summary Example (with Chain-of-Thought Reasoning)

**Patient Information:**  
REDACTED_NAME, a REDACTED_AGE-year-old REDACTED_GENDER, was admitted on 2024-03-12 and discharged on 2024-03-16.

**Diagnosis:**  
Intracerebral hemorrhage, unspecified (ICD-10: I61.9)

**Summary of Care:**  
→ The patient presented with confusion and right-sided weakness following a fall.  
→ CT imaging confirmed a right hemispheric intracerebral hemorrhage.  
→ Mannitol was administered to reduce cerebral edema, and antihypertensives were used to control blood pressure.  
→ Neurological status was closely monitored with serial GCS scoring and vital signs.  
→ Over 72 hours, GCS remained stable at 14, and no further neurological deterioration was noted.  
→ The patient showed gradual improvement in orientation and physical mobility.

**Disposition:**  
→ With stable neurological findings and no signs of worsening edema, the patient was deemed clinically stable.  
→ Family members were educated on home safety measures.  
→ The patient was discharged to home care under supervision.

**Follow-up Plan:**  
→ Outpatient neurology follow-up in one week.  
→ Repeat CT scan ordered in 2 weeks.  
→ Family advised on red flag symptoms (e.g., headache, confusion, vomiting).

**Contact:**  
Neurology clinic contact provided for emergencies.  
Sincerely,  
REDACTED_DOCTOR

---

Discharge Summary Example (with Chain-of-Thought Reasoning)

**Patient Information:**  
REDACTED_NAME, a REDACTED_AGE-year-old REDACTED_GENDER, was admitted on 2024-03-08 and discharged on 2024-03-12.

**Diagnosis:**  
ST-elevation myocardial infarction (STEMI) — no PCI performed

**Summary of Care:**  
→ The patient presented with chest pain and ECG showing ST-elevation.  
→ Labs showed elevated troponin confirming myocardial injury.  
→ Cardiology was contacted, but PCI was not performed due to service limitations.  
→ Instead, the patient was treated medically with aspirin, heparin, and supportive care.  
→ By Day 3, the chest pain had resolved, and vitals were stable.  
→ The patient expressed a strong desire to be discharged and declined further hospital stay.  
→ Risk of early discharge was discussed, and the patient acknowledged understanding.

**Disposition:**  
→ While guideline-based PCI was not administered, the patient's symptoms resolved, and discharge was deemed acceptable under the circumstances.  
→ The care team documented the system-level barriers and patient’s informed decision.

**Follow-up Plan:**  
→ Outpatient cardiology appointment arranged within 1 week.  
→ Patient instructed to return immediately if chest pain or symptoms recur.

**Contact:**  
Contact cardiology department for any concerns.  
Sincerely,  
REDACTED_DOCTOR
""".strip()

def few_shot_safety_examples():
    return """
Example 1

Summary:
The patient had pneumonia and was treated with IV and oral antibiotics. Vitals stabilized, fever resolved, and the patient was afebrile for 48 hours prior to discharge.

Reasoning:
The infection was treated effectively. Objective signs (temperature, vitals) normalized. The discharge aligns with clinical guidelines.

Answer: Yes

---

Example 2

Summary:
The patient had a STEMI but did not receive PCI due to system limitations. Chest pain resolved, and the patient requested discharge. Risks were discussed and documented.

Reasoning:
Although PCI was not performed, the patient’s symptoms resolved, and they made an informed decision. This is a medically explainable discharge given the context.

Answer: Yes

---

Example 3

Summary:
The patient presented with new-onset seizures and was started on medication. No imaging or EEG was done. The patient was discharged 12 hours later.

Reasoning:
Discharging a patient with a new seizure disorder without diagnostic evaluation or monitoring is premature and unsafe.

Answer: No

---

Example 4

Summary:
The patient had fever, confusion, and possible UTI. Antibiotics were started, but the patient became drowsy. They were still febrile at discharge.

Reasoning:
There were unresolved symptoms and new red flags (drowsiness). The discharge appears unsafe.

Answer: No

---

Example 5

Summary:
The patient had lobar pneumonia with initial fever, cough, and hypoxia. CRP and WBC were elevated. Over several days, temperature normalized, oxygen saturation rose to 98%, and CRP decreased. The patient was transitioned to oral antibiotics and was tolerating oral intake well.

Reasoning:
This is a clear recovery pattern. Objective trends show resolution of infection. The patient met standard discharge criteria and was discharged with follow-up.

Answer: Yes
---

Example 6

Summary:
The patient had a STEMI and underwent PCI on admission day. Post-procedure, chest pain resolved and cardiac enzymes trended down. The patient remained hemodynamically stable, was started on dual antiplatelet therapy, and had no complications during the stay.

Reasoning:
The patient received guideline-recommended treatment with PCI. The resolution of symptoms, improving labs, and stable vitals support discharge. This is a textbook safe discharge.

Answer: Yes

---

Example 7

Summary:
The patient presented with a seizure and was found to have hyponatremia. Sodium was corrected with IV saline. No additional seizures occurred. The patient was alert, oriented, and stable at discharge. Outpatient neurology and labs were arranged.

Reasoning:
The seizure had a reversible metabolic cause. The underlying issue was treated and the patient was monitored. Discharge is reasonable with follow-up.

Answer: Yes

---

Example 8

Summary:
The patient presented with a generalized seizure. Labs revealed hyponatremia which was corrected. No EEG or neuroimaging was done. The patient was discharged 8 hours later with no further events documented.

Reasoning:
Although a reversible cause was addressed, no diagnostic workup (imaging, EEG) was performed to rule out other etiologies. Rapid discharge without neurological assessment is premature and potentially unsafe.

Answer: No
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
Date: {data.get('discharge_date', 'Unknown')}
Patient: REDACTED_NAME  
Age: REDACTED_AGE  
Gender: REDACTED_GENDER  
Admission Date: {data.get('admit_date', '')}  
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
- Reasoning behind clinical decisions (chain of thought)
- Admission and discharge dates
- Trends in labs/vitals without overlisting
- Recovery status and follow-up expectations
- If discharge occurred without full standard treatment, clarify the reason (e.g., patient preference, system limitations).

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
Each item should include a \"text\" field with the exact phrase and a \"category\" field from this set:
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
Evaluate this discharge summary and determine whether, based on the documented care and outcome, the patient was discharged in a medically explainable way.

Consider whether diagnostic workup, clinical stability, and discharge criteria are clearly documented. If there are unresolved symptoms, incomplete monitoring, or premature discharge, mark it as "No" or "Uncertain" and explain why.

Return one of: "Yes", "No", or "Uncertain", and explain why using reasoning steps.

{few_shot_safety_examples()}

---

Summary:
{summary_text}
"""

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content.strip()
