import json
import logging
from openai import OpenAI
import re

logging.basicConfig(filename="logs/discharge_summary.log", level=logging.INFO)

def load_patient_data(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def few_shot_examples():
    return """
Discharge Letter

Dear REDACTED_NAME,

I am writing to inform you that you are being discharged from the hospital after receiving treatment for lobar pneumonia. You were admitted on REDACTED_ADMIT_DATE, and the improvement in your condition allows for your discharge on REDACTED_DISCHARGE_DATE.

Patient Information:
- Name: REDACTED_NAME
- Age: REDACTED_AGE
- Gender: REDACTED_GENDER
- Patient ID: REDACTED_ID
- Admission Date: REDACTED_ADMIT_DATE
- Discharge Date: REDACTED_DISCHARGE_DATE

Diagnosis:
- Lobar pneumonia, unspecified organism (J18.1)
- DRG Code: 193 - Simple pneumonia and pleurisy with MCC

Encounters:
- Admitted on REDACTED_ADMIT_DATE, with symptoms of cough, shortness of breath, hemoptysis, and fever
- Discharged on REDACTED_DISCHARGE_DATE

Medical Summary:
- Patient presented with lobar pneumonia with consolidation in the left lower lobe on the chest X-ray.
- Initial vital signs on admission showed a temperature of 38.5°C, heart rate of 90 bpm, blood pressure of 130/85 mmHg, respiratory rate of 20 breaths/min, and oxygen saturation of 92%.
- Throughout the admission, there was a gradual improvement in the patient's condition.
- Laboratory results showed a decrease in CRP levels, WBC count, and normalization of other parameters.
- Medication regimen included IV Amoxicillin, Paracetamol, and Atorvastatin, with a transition to oral antibiotics near discharge.

Plan:
- Patient responded well to treatment and is medically fit for discharge.
- Instructions for continuing oral antibiotics at home for 5 more days.
- Follow-up appointment scheduled in the outpatient clinic in two weeks.

Please feel free to contact our clinic for any further questions or concerns.

Sincerely,  
REDACTED_DOCTOR

---

Date: REDACTED_DISCHARGE_DATE  
Patient: REDACTED_NAME (Patient ID: REDACTED_ID)  
Age: REDACTED_AGE  
Gender: REDACTED_GENDER  

Dear REDACTED_NAME,

I am writing to inform you that you are being discharged from the hospital after receiving treatment for lobar pneumonia. You were admitted on REDACTED_ADMIT_DATE, and the improvement in your condition allows for your discharge on REDACTED_DISCHARGE_DATE.

Diagnosis:
- Lobar pneumonia, unspecified organism (J18.1)
- Simple pneumonia and pleurisy with MCC (DRG code: 193)

Summary of care:
- You were admitted with symptoms of cough, shortness of breath, hemoptysis, and fever.
- Imaging showed consolidation in the left lower lobe.
- Lab results indicated improvement in CRP, WBC, hemoglobin, and platelet levels.
- Empirical antibiotic therapy with Amoxicillin IV and oral medications were administered.
- Vital signs and oxygen saturation remained stable and improved over the course of your stay.

Disposition:
- You are deemed medically fit for discharge and can continue your recovery at home.
- Instructions for oral antibiotics for 5 more days have been provided.
- A follow-up appointment at the outpatient clinic in two weeks is scheduled for further monitoring.

Please adhere to the prescribed treatment plan and follow-up appointments for a complete recovery. If you experience any worsening symptoms or have concerns, do not hesitate to contact us.

Take care and best wishes for your continued health and well-being.

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
        f"- {m['medication']} {m['dose']} ({m.get('frequency', 'N/A')})"
        for m in data.get("med_orders", [])
    ])
    notes = "\n".join([
        f"{n.get('date', '')} - {n.get('content', n.get('note', ''))}"
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

Please generate a discharge summary that includes all of the following sections:

- **Patient Information**: Name, age, gender, dates of admission and discharge.  
- **Diagnosis**: All recorded diagnoses (include ICD/DRG codes if available).  
- **Summary of Care**: Presenting symptoms, vitals, imaging findings, lab trends, treatments provided (medications, interventions).  
- **Disposition**: Discharge status and instructions.  
- **Follow-up Plan**: Appointments or further evaluations.  
- **Contact**: Sign off with the treating physician's name.

🔒 Use the following placeholders **exactly as shown**, with no quotes, brackets, or formatting:  
REDACTED_NAME, REDACTED_AGE, REDACTED_GENDER, REDACTED_ID, REDACTED_ADMIT_DATE, REDACTED_DISCHARGE_DATE, REDACTED_DOCTOR

The tone should be professional and understandable to patients, families, and clinicians. Organize sections clearly and use bullet points where appropriate.

Sign off with:  
Sincerely,  
REDACTED_DOCTOR
""".strip()

    if few_shot:
        full_prompt = few_shot_examples() + "\n\n---\n\n" + prompt_body
    else:
        full_prompt = prompt_body

    logging.info("\n" + "="*20 + " PROMPT " + "="*20 + "\n" + full_prompt)
    return full_prompt

def get_discharge_summary(data, api_key, few_shot=True, model="gpt-3.5-turbo", additional_instruction=""):
    prompt = generate_prompt(data, few_shot)

    if additional_instruction.strip():
        prompt += f"\n\n# Additional Instruction:\n{additional_instruction.strip()}"
        
    # Add explicit instruction for proper spacing and formatting, but preserve placeholders exactly
    prompt += "\n\nIMPORTANT: Ensure proper spacing between words and after punctuation. Use clear paragraph breaks. DO NOT add any spaces or characters within placeholders like REDACTED_NAME - keep them exactly as written."

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )

    result = response.choices[0].message.content
    
    # Post-process to fix formatting issues, but carefully to avoid breaking placeholders
    # 1. Add space between letters and complete REDACTED_ placeholders
    placeholders = ["REDACTED_NAME", "REDACTED_AGE", "REDACTED_GENDER", "REDACTED_ADMIT_DATE", 
                   "REDACTED_DISCHARGE_DATE", "REDACTED_ID", "REDACTED_DOCTOR"]
    
    for placeholder in placeholders:
        # Add space before placeholder if there's text directly before it
        result = re.sub(r'([a-zA-Z0-9])' + re.escape(placeholder), r'\1 ' + placeholder, result)
        
        # Add space after placeholder if there's text directly after it
        result = re.sub(re.escape(placeholder) + r'([a-zA-Z0-9])', placeholder + r' \1', result)
    
    # 2. Ensure proper spacing after punctuation (but not within placeholders)
    result = re.sub(r'([.,:;!?])([a-zA-Z0-9])(?!(_|\s*_))', r'\1 \2', result)
    
    # 3. Fix potential run-on lines for section headers
    section_headers = ["Patient Information:", "Diagnosis:", "Summary of Care:", "Disposition:", "Follow-up Plan:"]
    for header in section_headers:
        result = re.sub(r'([a-zA-Z])' + re.escape(header), r'\1\n\n' + header, result)
    
    logging.info("\n" + "="*20 + " RESPONSE " + "="*20 + "\n" + result)
    return result