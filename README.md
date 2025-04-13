# 🏥 LLM-Powered Discharge Summary Generator

This is a secure, LLM-assisted prototype for generating patient discharge summaries based on structured inpatient data. The tool ensures clarity, privacy, safety, and clinical relevance in discharge documentation using OpenAI models via few-shot and chain-of-thought prompting.

---

## 🧩 What This Tool Does

- ✅ Accepts structured inpatient JSON data as input
- ✅ Redacts PII before generating summaries using LLMs
- ✅ Uses prompt engineering with few-shot + chain-of-thought reasoning
- ✅ Produces clear, paragraph-based summaries formatted by clinical section
- ✅ Validates discharge safety with a second LLM call
- ✅ Extracts highlights (important clinical insights) with a third LLM call
- ✅ Allows editing and evaluation of summaries
- ✅ Provides De-Identified and Identified viewing modes
- ✅ Implements logging, readability scoring, and manual review checklist

---

## 🚀 How to Use the App

### 🧱 Requirements

- Python 3.9+
- OpenAI API Key
- Dependencies (install with `pip install -r requirements.txt`):
  - `streamlit`
  - `openai`
  - `textstat`

### 🖥️ Launch

```bash
streamlit run app.py
```

### 🧭 User Flow

1. **Enter OpenAI API key** in the sidebar.
2. **Choose a model** (`gpt-3.5-turbo` or `gpt-4`) and temperature.
3. **Select a patient record JSON file** from the dropdown.
4. **(Optional)** Add additional prompt instructions (e.g., "Emphasize follow-up care").
5. **Click "Generate Summary"** — the app:
    - Redacts PII
    - Uses a few-shot + chain-of-thought prompt
    - Sends to OpenAI LLM
    - Inserts PII back (only for Identified View)
6. Choose a view mode:
    - **De-Identified View**: Hides all PII
    - **Identified View**: Shows the restored personal info (name, gender, age, etc.)
7. Review or edit the summary
8. Evaluate clarity, specificity, accuracy, and PII privacy using checkboxes

---

## 🔒 Privacy & Safety Implementation

This app was designed to follow the **“privacy by default”** principle, ensuring that no patient-identifiable data is ever exposed to external APIs. All core logic is designed around secure redaction, localized PII restoration, and patient safety enforcement.

### 🔐 No PII Sent to LLM

Before calling the OpenAI API, the app **removes all personally identifiable information** (PII) from the patient record and replaces it with safe placeholders:

| Field               | Placeholder         |
|--------------------|---------------------|
| Patient Name       | `REDACTED_NAME`     |
| Gender             | `REDACTED_GENDER`   |
| Age                | `REDACTED_AGE`      |
| Doctor's Name      | `REDACTED_DOCTOR`   |

✅ These placeholders remain throughout the entire prompt construction and LLM response.  
✅ The redacted prompt is **the only thing sent to OpenAI’s API**.  
✅ Admission and discharge dates are retained, as they are clinically relevant and not uniquely identifying.

### 🔍 Redaction & Reinsertion Logic

Located in `utils.py`, the redaction logic:

- Makes a **deep copy** of the original patient data
- Redacts PII fields before prompt generation
- Keeps original data locally
- Uses a dedicated `insert_pii()` function to re-populate the summary **only after the LLM has responded**, ensuring data never leaves the local machine

```python
summary_with_pii = insert_pii(summary_redacted, patient_data)
```

This happens **only** in the Identified View. De-Identified View always keeps placeholders.

### 🧠 View Modes (User-Controlled Privacy)

Users can toggle between two privacy modes:

- **🔒 De-Identified View**: Summary with redacted placeholders only. This is the default mode.
- **🧑 Identified View**: Summary with personal details restored from the original JSON — shown only in the UI, never sent or logged externally.

### 🔐 Dual Logging

- `log_deidentified.log`: Contains only placeholder-based summaries and safe metadata
- `log_identified.log`: Logs PII-containing output, but only locally
- Logs include prompt(s), summary, LLM highlights, safety status, and manual evaluation data

### 🛡️ Discharge Safety Enforcement (Hard Stop)

To prevent medically unsafe discharge summaries from being generated, the app checks for red-flag conditions in clinical notes.

In `utils.py`:

```python
if not is_safe_for_discharge(data):
    st.error("Patient is not medically fit for discharge.")
    st.stop()
```

#### How the Safety Check Works:

- It scans both `notes` and `ward_round_notes` fields
- Searches for phrases like:
  - `not safe for discharge`
  - `condition remains critical`
  - `unfit for discharge`
  - `requires close monitoring`

If matched, summary generation is blocked.

### ✅ Additional Safeguards Implemented

- **PII Logging Segregation**: Logs from Identified and De-Identified modes are separated
- **PII Placeholder Consistency**: LLM is explicitly instructed not to alter placeholders
- **Local Editing Only**: Users may edit the summary locally, but no edited text is sent back to the LLM
- **Manual Evaluation Checklist**: Users confirm privacy, accuracy, and structure in each summary before finalizing
- **Robust Fallbacks**: If the discharging doctor is not found in notes, the system falls back to `"Discharging Doctor"`

---

## 🧠 Prompt Engineering

### ✅ Few-Shot + Chain-of-Thought

Each prompt includes:
- Two complete discharge letter examples
- Realistic section headers
- Clinical logic (e.g., lab trends, interventions, recovery)
- Explicit LLM instruction to reason step-by-step

### Example Sections in Generated Output

- **Patient Information**
- **Diagnosis**
- **Summary of Care**
- **Disposition**
- **Follow-up Plan**
- **Contact**

All sections are prose — no bullet points.

---

## 📊 Evaluation Features

- **Flesch Reading Ease Score**
- **Highlight Extraction Coverage**
- **Discharge Safety LLM Check**
- **Manual Evaluation Checklist**
- Logged to:
  - `log_deidentified.log`
  - `log_identified.log`

---

## 🧪 API Usage Summary

For each summary generation:

| API Call | Purpose |
|----------|---------|
| ✅ 1st    | Generate discharge summary |
| ✅ 2nd    | Extract key clinical highlights |
| ✅ 3rd    | Evaluate discharge safety |

---

## 📦 Folder Structure

```
├── app.py                    # Streamlit UI logic
├── summary_generator.py     # LLM interaction logic
├── utils.py                 # PII redaction/insertion + safety check
├── data/                    # Patient JSON files
├── logs/                    # Separate logs for private/personal views
├── requirements.txt         # Dependencies
```

---

## ✅ How We Meet the Prototype Requirements

| Requirement                           | Status     | Notes |
|--------------------------------------|------------|-------|
| LLM use with few-shot + reasoning    | ✅ Completed | Uses few-shot prompting with reasoning chain |
| Logging prompts + responses          | ✅ Completed | Logs to separate files for private/personal |
| Secure UI with patient file input    | ✅ Completed | All inputs handled through UI |
| Editing and feedback mechanism       | ✅ Completed | Editable summary + checkbox feedback |
| Safety check before generation       | ✅ Completed | No summary if "not fit for discharge" |
| Avoid sending PII to LLM             | ✅ Completed | PII replaced before generation |
| Show personalized output locally     | ✅ Completed | Restores PII in Identified View only |
| Structured summary output            | ✅ Completed | Matches clinical format with prose |
| No unnecessary labs/notes            | ✅ Completed | Prompt filters by trend, not dumps |
| Uses 3 OpenAI API calls               | ✅ Completed | Generation + highlights + safety |

---

## 🛠️ Limitations

- Some safety logic depends on clinical text quality
- Highlights are extracted by LLM and not manually verified
- Not yet integrated with electronic health records (EHR)
- Summaries are based on synthetic data; real-world deployment would require HIPAA compliance

---

## 👩‍⚕️ Stakeholders

- Clinicians needing to reduce documentation time
- Hospitals aiming to streamline discharge workflow
- Developers seeking safe LLM integration patterns in health tech

---

## 👏 Credits

This project was built for the 90-835 Spring 2025 course  
"Designing Smart and Healthy Systems"
