# 🏥 LLM-Powered Discharge Summary Generator

A smart, patient-friendly discharge summary generation system that uses large language models (LLMs) to create, highlight, and validate summaries from structured patient data.

Built with **Streamlit** for the frontend and **OpenAI’s API** for language generation, this system aligns with best practices in clinical documentation, patient safety, and explainability.

---

## 📄 Project Overview

This application automatically generates a well-structured discharge summary for a hospital patient, incorporating:

- Structured clinical notes, medications, and diagnoses
- Patient-friendly, paragraph-formatted summary using LLMs
- Highlighting of critical clinical terms (e.g., diagnosis, follow-up)
- Safety validation of discharge readiness using a second LLM call
- Manual and automated evaluation metrics for completeness and correctness
- Full PII protection through redaction and controlled reinsertion

The tool supports care continuity between hospital and outpatient clinicians and improves the clarity of discharge communication for patients and families.

---

## ✅ Key Features

### 🧠 LLM-Based Summary Generation
- Uses **few-shot learning** with **chain-of-thought prompting**
- Includes 2 sample summaries as prompting context
- Summarizes diagnosis, labs, medications, condition, and disposition
- Output uses prose (not bullets) and section headers like:

  ```
  - Patient Information
  - Diagnosis
  - Summary of Care
  - Disposition
  - Follow-up Plan
  - Contact
  ```

---

### 🖍️ Highlight Extraction (2nd LLM Call)
- Extracts phrases like:
  ```
  “diagnosed with lobar pneumonia” — diagnosis
  “5 more days” — duration
  “CRP and WBC declining” — clinical trend
  ```
- Bolded in the final rendered summary for easy scanning

---

### 🛡️ Discharge Safety Validation (3rd LLM Call)
- Asks: *“Is this patient safe to discharge?”*
- Returns “Yes”, “No”, or “Uncertain” + reasoning
- Ensures the LLM acts as a safeguard to catch errors or inconsistencies

---

### 🔐 PII Protection
- Patient names, dates of birth, and other identifiers are **redacted before sending to the LLM**
- Redacted terms include: `REDACTED_NAME`, `REDACTED_AGE`, `REDACTED_DOCTOR`, etc.
- PII is reinserted after generation for display only
- Nothing personally identifiable is ever sent to OpenAI

---

### 📊 Evaluation System

Combines automatic and manual evaluation to systematically assess output quality.

| Metric | Type | Description |
|--------|------|-------------|
| Readability | Auto | Flesch Reading Ease Score |
| Highlight Coverage | Auto | % of expected clinical concepts present |
| Discharge Validation | Auto | LLM determines if discharge is appropriate |
| Evaluation Checklist | Manual | User confirms clarity, accuracy, and presence of key sections |
| Feedback Logging | Auto | All inputs, outputs, and feedback logged to file |

---

### 🖥️ Streamlit Frontend

- Upload/select patient record (JSON)
- Enter OpenAI API key (securely)
- Provide a custom prompt (optional)
- Click to generate summary
- Edit if needed
- See highlights, safety validation, readability, and submit feedback

---

## 📂 Folder Structure

```
📁 discharge_summary_app/
├── app.py                  # Main Streamlit app
├── summary_generator.py    # LLM prompts, few-shots, highlight + safety
├── utils.py                # Redaction, reinsertion, discharge checks
├── data/                   # Folder for patient JSON files
├── logs/                   # Stores summary logs + evaluation logs
├── requirements.txt        # Dependency file
└── README.md               # You're here
```

---

## 🧪 Example Workflow

1. Select patient file: `data_3.json`
2. Enter a prompt: `"Generate a discharge summary suitable for patients and outpatient clinicians."`
3. LLM generates discharge summary
4. Highlights like `"IV antibiotics"`, `"follow-up in 2 weeks"` are bolded
5. System checks if discharge is medically safe
6. You can edit the summary if needed
7. View:
   - Readability Score: `72.5`
   - Highlight Coverage: `100%`
   - LLM Validation: `"Yes — patient clinically stable for discharge"`
8. Submit evaluation checklist (logged)

---

## 📦 Installation

### 1. Clone the repo

```bash
git clone https://github.com/your-repo/discharge-summary-generator.git
cd discharge-summary-generator
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

---

## 🔑 Requirements

```
streamlit
openai>=1.0.0
textstat
python-dotenv (optional)
```

---

## 🚀 Project Goals

- Improve discharge safety and continuity of care using LLMs
- Support both clinicians and patients with understandable, accurate summaries
- Encourage explainability and systematic evaluation of LLM outputs
- Design a system aligned with **real-world healthcare** documentation standards

---

## 📚 References

- [Geeky Medics: How to Write a Discharge Summary](https://geekymedics.com/how-to-write-a-discharge-summary/)
- Final Project Brief: Designing Smart and Healthy Systems (90-835 Spring 2025)

---

## 🧑‍💻 Authors

- Your Name Here