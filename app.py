import os
import streamlit as st
import textstat
import logging
import json
import re
from datetime import datetime
from openai import OpenAIError
from summary_generator import (
    load_patient_data,
    get_discharge_summary,
    extract_highlights,
    validate_discharge_safety,
)
from utils import is_safe_for_discharge, redact_pii, insert_pii, passes_specificity_check

# --- App Config ---
st.set_page_config(page_title="Discharge Summary Generator", layout="wide")
st.title("🏥 LLM-Powered Discharge Summary Generator")

# --- Logging ---
logging.basicConfig(
    filename="logs/user_prompt_log.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Sidebar: API key and model ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("🔑 OpenAI API Key", type="password")
    model_name = st.selectbox("🧠 Model", ["gpt-3.5-turbo", "gpt-4"])
    temperature = st.slider("🌡️ Temperature", 0.0, 1.0, 0.6)

# --- File input ---
st.subheader("📂 Generate Summary from Patient Record")
json_files = [f for f in os.listdir("data") if f.endswith(".json")]
selected_file = st.selectbox("Select patient data file", json_files)
data_path = os.path.join("data", selected_file)

# --- Load and redact patient data ---
patient_data = load_patient_data(data_path)
redacted_data = redact_pii(patient_data)

st.radio("Prompt Method", ["Few-shot with Chain-of-Thought reasoning"], index=0, disabled=True)

# --- User input for LLM instruction ---
additional_prompt = st.text_area(
    "💬 Required: Enter a prompt to guide the LLM",
    placeholder="E.g., Write a discharge summary suitable for patients and clinicians.",
    height=100,
)

generate_btn = st.button("📝 Generate Summary")

# --- Session state ---
if "final_summary" not in st.session_state:
    st.session_state.final_summary = ""
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "highlights" not in st.session_state:
    st.session_state.highlights = []
if "safety_validation" not in st.session_state:
    st.session_state.safety_validation = ""

# --- Generate summary with validation ---
if generate_btn:
    if not api_key:
        st.warning("Please enter your OpenAI API key.")
        st.stop()
    if not additional_prompt.strip():
        st.warning("Please provide a prompt before generating the summary.")
        st.stop()
    if not is_safe_for_discharge(patient_data):
        st.error("❌ Patient is not medically fit for discharge.")
        st.stop()

    try:
        with st.spinner("Generating discharge summary..."):
            summary = get_discharge_summary(
                redacted_data,
                api_key,
                few_shot=True,
                model=model_name,
                additional_instruction=additional_prompt,
            )
            summary = insert_pii(summary, patient_data)
            st.session_state.final_summary = summary
            st.session_state.edit_mode = False
            st.success("✅ Summary generated.")

        # Extract highlights (2nd API call)
        with st.spinner("Extracting key highlights..."):
            st.session_state.highlights = extract_highlights(summary, api_key)

        # Validate discharge safety (3rd API call)
        with st.spinner("Running discharge safety check..."):
            st.session_state.safety_validation = validate_discharge_safety(summary, api_key)

        # Logging
        logging.info("=" * 60 + f"\n[SUMMARY GENERATED] {datetime.now()}\n" + "-" * 60)
        logging.info(f"FILE: {selected_file}")
        logging.info(f"USER PROMPT:\n{additional_prompt.strip()}")
        logging.info(f"OUTPUT:\n{summary}")
        logging.info(f"HIGHLIGHTS:\n{st.session_state.highlights}")
        logging.info(f"SAFETY VALIDATION:\n{st.session_state.safety_validation}")
        logging.info("=" * 60)

    except OpenAIError as e:
        st.error("❌ Invalid API key or OpenAI service error. Please check your key and try again.")
        logging.error(f"OpenAI API Error: {str(e)}")
        st.stop()

# --- Summary view + editing ---
if st.session_state.final_summary:
    st.markdown("### 📄 Discharge Summary")

    if st.session_state.edit_mode:
        edited = st.text_area("📝 Edit Discharge Summary", st.session_state.final_summary, height=500)
        if st.button("💾 Save Changes"):
            st.session_state.final_summary = edited
            st.session_state.edit_mode = False
            st.success("✅ Summary updated.")
    else:
        display_text = st.session_state.final_summary

        # Bold section headers
        section_headers = [
            "Patient Information:", "Diagnosis:", "Summary of Care:",
            "Disposition:", "Follow-up Plan:", "Contact:"
        ]
        for header in section_headers:
            display_text = re.sub(rf"(?<!\*)({re.escape(header)})", r"**\1**", display_text)

        # Bold phrases from LLM-extracted highlights
        for item in st.session_state.highlights:
            phrase = re.escape(item["text"])
            display_text = re.sub(rf"(?<!\*)({phrase})(?!\*)", r"**\1**", display_text, flags=re.IGNORECASE)

        st.markdown(display_text, unsafe_allow_html=True)

        if st.button("✏️ Edit Summary"):
            st.session_state.edit_mode = True

    # --- Evaluation Metrics ---
    st.markdown("### 🧪 Evaluation Results")

    # Readability
    readability = textstat.flesch_reading_ease(st.session_state.final_summary)
    st.metric("📖 Readability (Flesch Score)", readability)

    # Highlight coverage
    expected_categories = {
        "diagnosis", "medication", "followup_action", "discharge_criteria", "recovery_status"
    }
    found_categories = set([item["category"] for item in st.session_state.highlights])
    coverage_score = len(expected_categories & found_categories) / len(expected_categories)
    st.progress(coverage_score, text=f"🧪 Highlight Coverage: {int(coverage_score * 100)}%")

    # Safety validation
    if st.session_state.safety_validation:
        st.markdown("### 🛡️ Discharge Safety Validation")
        st.markdown(st.session_state.safety_validation)

    # Manual evaluation checklist
    st.markdown("### 📝 Evaluation Checklist")
    clarity = st.checkbox("✅ Clarity and completeness")
    specificity = st.checkbox("✅ Specific care & follow-up details")
    correctness = st.checkbox("✅ Information appears accurate and medically sound")
    sections = st.checkbox("✅ Includes all required sections (Diagnosis, Summary, Disposition, etc.)")
    no_pii = st.checkbox("✅ No PII passed to LLM")

    if st.button("✅ Submit Evaluation"):
        feedback_log = {
            "clarity": clarity,
            "specificity": specificity,
            "correctness": correctness,
            "sections_present": sections,
            "no_pii": no_pii,
            "highlight_coverage": f"{int(coverage_score * 100)}%",
            "readability_score": readability,
            "safety_validation": st.session_state.safety_validation,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": selected_file,
        }
        logging.info("[EVALUATION SUBMITTED]")
        logging.info(json.dumps(feedback_log, indent=2))
        st.success("✅ Evaluation submitted and logged.")
