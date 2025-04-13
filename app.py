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
from utils import is_safe_for_discharge, redact_pii, insert_pii

# --- Constants ---
DEFAULT_SYSTEM_PROMPT = "Write a clear and complete discharge summary for the patient described in this data."

# --- App Config ---
st.set_page_config(page_title="Discharge Summary Generator", layout="wide")
st.title("🏥 LLM-Powered Discharge Summary Generator")

# --- Sidebar: API key and model ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("🔑 OpenAI API Key", type="password")
    model_name = st.selectbox("🧠 Model", ["gpt-3.5-turbo", "gpt-4"])
    temperature = st.slider("🌡️ Temperature", 0.0, 1.0, 0.6)
    st.caption("📘 Temperature controls creativity: lower = more focused, higher = more diverse responses.")

# --- File input ---
st.subheader("📂 Generate Summary from Patient Record")
json_files = [f for f in os.listdir("data") if f.endswith(".json")]

if "last_selected_file" not in st.session_state:
    st.session_state.last_selected_file = ""

selected_file = st.selectbox("Select patient data file", json_files)

# Clear state when switching files
if selected_file != st.session_state.last_selected_file:
    st.session_state.last_selected_file = selected_file
    st.session_state.summary_redacted = ""
    st.session_state.summary_with_pii = ""
    st.session_state.highlights = []
    st.session_state.safety_validation = ""
    for key in list(st.session_state.keys()):
        if key.endswith("_edit_mode") or key.endswith("_editor"):
            del st.session_state[key]

data_path = os.path.join("data", selected_file)
patient_data = load_patient_data(data_path)
redacted_data = redact_pii(patient_data)

# --- Prompt input ---
st.radio("Prompt Method", ["Few-shot with Chain-of-Thought reasoning"], index=0, disabled=True)
additional_prompt = st.text_area(
    "📝 Optional: Add extra instruction to guide the LLM",
    placeholder="E.g., Emphasize follow-up plans if any...",
    height=100,
)
st.caption("💡 If left blank, the summary will be generated with a default instruction.")
generate_btn = st.button("📝 Generate Summary")
# --- Session state initialization ---
if "summary_redacted" not in st.session_state:
    st.session_state.summary_redacted = ""
if "summary_with_pii" not in st.session_state:
    st.session_state.summary_with_pii = ""
if "highlights" not in st.session_state:
    st.session_state.highlights = []
if "safety_validation" not in st.session_state:
    st.session_state.safety_validation = ""

# --- Generate Summary ---
if generate_btn:
    if not api_key:
        st.warning("Please enter your OpenAI API key.")
        st.stop()
    if not is_safe_for_discharge(patient_data):
        st.error("❌ Patient is not medically fit for discharge.")
        st.stop()

    try:
        combined_prompt = DEFAULT_SYSTEM_PROMPT
        if additional_prompt.strip():
            combined_prompt += f"\n\n{additional_prompt.strip()}"

        with st.spinner("Generating discharge summary..."):
            summary_redacted = get_discharge_summary(
                redacted_data,
                api_key,
                few_shot=True,
                model=model_name,
                additional_instruction=combined_prompt,
            )
            summary_with_pii = insert_pii(summary_redacted, patient_data)
            highlights = extract_highlights(summary_redacted, api_key)
            safety = validate_discharge_safety(summary_redacted, api_key)

            st.session_state.summary_redacted = summary_redacted
            st.session_state.summary_with_pii = summary_with_pii
            st.session_state.highlights = highlights
            st.session_state.safety_validation = safety

        # --- Logging (Private) ---
        with open("logs/log_deidentified.log", "a") as f:
            f.write("="*60 + f"\n[SUMMARY GENERATED] {datetime.now()}\n" + "-"*60 + "\n")
            f.write(f"FILE: {selected_file}\n")
            f.write(f"SYSTEM PROMPT:\n{DEFAULT_SYSTEM_PROMPT}\n")
            f.write(f"USER PROMPT:\n{additional_prompt.strip() or '[None]'}\n")
            f.write(f"FULL PROMPT SENT TO LLM:\n{combined_prompt}\n")
            f.write(f"OUTPUT (REDACTED):\n{summary_redacted}\n")
            f.write(f"HIGHLIGHTS:\n{json.dumps(highlights)}\n")
            f.write(f"SAFETY VALIDATION:\n{safety}\n")
            f.write("="*60 + "\n")

        # --- Logging (Personal) ---
        with open("logs/log_identified.log", "a") as f:
            f.write("="*60 + f"\n[SUMMARY GENERATED] {datetime.now()}\n" + "-"*60 + "\n")
            f.write(f"FILE: {selected_file}\n")
            f.write(f"SYSTEM PROMPT:\n{DEFAULT_SYSTEM_PROMPT}\n")
            f.write(f"USER PROMPT:\n{additional_prompt.strip() or '[None]'}\n")
            f.write(f"FULL PROMPT SENT TO LLM:\n{combined_prompt}\n")
            f.write(f"OUTPUT (WITH PII):\n{summary_with_pii}\n")
            f.write(f"HIGHLIGHTS:\n{json.dumps(highlights)}\n")
            f.write(f"SAFETY VALIDATION:\n{safety}\n")
            f.write("="*60 + "\n")

    except OpenAIError as e:
        st.error("❌ OpenAI API Error. Please check your key and try again.")
        st.stop()
# --- Choose view mode (secure rendering) ---
st.subheader("🔒 Choose Display Mode")
view_mode = st.selectbox("Display Format", ["De-Identified View", "Identified View"])
st.caption("🧾 De-Identified View hides personal info. Identified View restores real names/dates after generation. No PII is ever sent to the LLM in either mode.")

# --- Unified rendering function ---
def render_summary(tab_name, state_key, log_file):
    summary_text = st.session_state.get(state_key, "")
    st.markdown(f"### {tab_name} Summary")

    if not summary_text:
        st.info("No summary generated yet.")
        return

    edit_key = f"{tab_name}_edit_mode"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    if st.session_state[edit_key]:
        new_text = st.text_area("📝 Edit Summary", summary_text, height=500, key=f"{tab_name}_editor")
        if st.button("💾 Save", key=f"{tab_name}_save"):
            st.session_state[state_key] = new_text
            st.session_state[edit_key] = False
            st.rerun()
    else:
        display_text = summary_text
        for section in ["Patient Information:", "Diagnosis:", "Summary of Care:", "Disposition:", "Follow-up Plan:", "Contact:"]:
            display_text = re.sub(rf"(?<!\*)({re.escape(section)})", r"**\1**", display_text)
        for item in st.session_state.highlights:
            phrase = re.escape(item["text"])
            display_text = re.sub(rf"(?<!\*)({phrase})(?!\*)", r"**\1**", display_text, flags=re.IGNORECASE)

        st.markdown(display_text, unsafe_allow_html=True)

        if st.button("✏️ Edit", key=f"{tab_name}_edit_btn"):
            st.session_state[edit_key] = True

    # --- Evaluation ---
    st.markdown("### 🧪 Evaluation Metrics")
    readability = textstat.flesch_reading_ease(summary_text)
    st.metric("📖 Readability", f"{readability:.2f}")

    expected = {"diagnosis", "medication", "followup_action", "discharge_criteria", "recovery_status"}
    actual = {item["category"] for item in st.session_state.highlights}
    coverage = len(expected & actual) / len(expected)
    st.progress(coverage, text=f"Highlight Coverage: {int(coverage * 100)}%")

    if st.session_state.safety_validation:
        st.markdown("### 🛡️ Safety Validation")
        st.markdown(st.session_state.safety_validation)

    st.markdown("### ✅ Evaluation Checklist")
    clarity = st.checkbox(f"{tab_name} - Clarity")
    specificity = st.checkbox(f"{tab_name} - Specificity")
    accuracy = st.checkbox(f"{tab_name} - Medically Accurate")
    sections = st.checkbox(f"{tab_name} - Has All Sections")
    no_pii = st.checkbox(f"{tab_name} - No PII sent to LLM")

    if st.button(f"📩 Submit Evaluation ({tab_name})", key=f"{tab_name}_submit"):
        eval_data = {
            "tab": tab_name,
            "clarity": clarity,
            "specificity": specificity,
            "correctness": accuracy,
            "sections_present": sections,
            "no_pii": no_pii,
            "highlight_coverage": f"{int(coverage * 100)}%",
            "readability_score": readability,
            "safety_validation": st.session_state.safety_validation,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": st.session_state.last_selected_file,
        }
        with open(f"logs/{log_file}", "a") as f:
            f.write(json.dumps(eval_data, indent=2) + "\n")
        st.success("✅ Evaluation logged.")

# --- Render the selected mode only ---
if view_mode == "De-Identified View":
    render_summary("De-Identified", "summary_redacted", "log_deidentified.log")
elif view_mode == "Identified View":
    render_summary("Identified", "summary_with_pii", "log_identified.log")

