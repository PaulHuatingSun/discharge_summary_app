import os
import streamlit as st
import textstat
import logging
import re
from summary_generator import load_patient_data, get_discharge_summary
from utils import is_safe_for_discharge, redact_pii, insert_pii, passes_specificity_check

st.set_page_config(page_title="Discharge Summary Generator", layout="wide")
st.title("🏥 LLM-Powered Discharge Summary Generator")

logging.basicConfig(filename="logs/user_prompt_log.log", level=logging.INFO)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("🔑 OpenAI API Key", type="password")
    model_name = st.selectbox("🧠 Model", ["gpt-3.5-turbo", "gpt-4"])
    temperature = st.slider("🌡️ Temperature", 0.0, 1.0, 0.6)
    mode = st.radio("🛠️ Mode", ["Structured Patient Data", "Manual Prompt (with data)"])

# ----------- STRUCTURED MODE -----------
if mode == "Structured Patient Data":
    st.subheader("📂 Generate Summary from Patient Record")
    json_files = [f for f in os.listdir("data") if f.endswith(".json")]
    selected_file = st.selectbox("Select patient data file", json_files)
    data_path = os.path.join("data", selected_file)

    # Load the original (unredacted) patient data
    patient_data = load_patient_data(data_path)

    # Redact a separate copy to send to the LLM
    redacted_data = redact_pii(patient_data)

    shot_type = st.radio("Prompt Type", ["Zero-shot", "Few-shot (includes example)"])
    use_few_shot = shot_type == "Few-shot (includes example)"

    additional_prompt = st.text_area(
        "💬 Optional: Add additional instructions to the LLM",
        placeholder="E.g., write in plain English, avoid abbreviations",
        height=100,
    )

    if st.button("📝 Generate Summary"):
        if not api_key:
            st.warning("Please enter your OpenAI API key.")
            st.stop()

        if not is_safe_for_discharge(patient_data):
            st.error("❌ Patient is not medically fit for discharge.")
            st.stop()

        with st.spinner("Generating summary..."):
            summary = get_discharge_summary(
                redacted_data,
                api_key,
                few_shot=use_few_shot,
                model=model_name,
                additional_instruction=additional_prompt,
            )

            # Insert real PII after generation
            summary = insert_pii(summary, patient_data)

            st.success("✅ Summary generated.")
            st.text_area("📄 Discharge Summary", summary, height=400)

            readability = textstat.flesch_reading_ease(summary)
            st.metric("📈 Readability (Flesch Score)", readability)

            if not passes_specificity_check(summary):
                st.warning("⚠️ May lack specific clinical instructions (follow-up, dosage, etc.)")

            st.markdown("### 🧪 Evaluation Checklist")
            clarity = st.checkbox("✅ Clarity and completeness")
            specificity = st.checkbox("✅ Specific care & follow-up details")
            safety = st.checkbox("✅ Medically appropriate for discharge")
            privacy = st.checkbox("✅ No PII passed to LLM")

            if st.button("✅ Submit Evaluation"):
                logging.info(
                    f"[STRUCTURED] File: {selected_file} | Prompt Type: {shot_type} | Extra Prompt: {additional_prompt}\nSUMMARY:\n{summary}"
                )
                logging.info(
                    f"Checklist - Clarity: {clarity}, Specificity: {specificity}, Safety: {safety}, Privacy: {privacy}"
                )
                st.success("✅ Feedback submitted and logged.")
# ----------- MANUAL PROMPT MODE -----------
else:
    st.subheader("✍️ Manual Prompt Input with Patient Data")

    json_files = [f for f in os.listdir("data") if f.endswith(".json")]
    selected_file = st.selectbox("📂 Select patient data file", json_files)
    filepath = os.path.join("data", selected_file)
    patient_data = load_patient_data(filepath)

    user_prompt = st.text_area(
        "📝 Ask a question or give instructions (optional)",
        placeholder="E.g., Write a discharge summary, or What medications was the patient on?",
        height=150
    )

    if st.button("🧠 Run Prompt"):
        if not api_key:
            st.warning("Please enter your OpenAI API key.")
            st.stop()

        # If user didn't write anything, fall back to a default prompt
        if not user_prompt.strip():
            user_prompt = "Write a clear and complete discharge summary for the patient described in this data."

        with st.spinner("Calling OpenAI..."):
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful medical assistant."},
                    {"role": "user", "content": f"{user_prompt}\n\nPatient Data:\n{patient_data}"}
                ],
                temperature=temperature,
            )

            result = response.choices[0].message.content

            st.success("✅ Response generated.")
            st.markdown("### 📄 LLM Output")
            st.markdown(result)

            logging.info(
                f"[MANUAL MODE] File: {selected_file}\nPROMPT:\n{user_prompt}\nRESPONSE:\n{result}"
            )