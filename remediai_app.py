import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- 1. SETUP ---
st.set_page_config(page_title="RemediAI: Full Diagnostic Cycle", layout="wide")

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing!")
    st.stop()

# --- 2. SMART DATA LOAD ---
@st.cache_data
def load_vetted_db():
    db_file = next((f for f in os.listdir(".") if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv"))), None)
    if db_file:
        sep = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=sep)
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_vetted_db()

# --- 3. THE WORKFLOW TABS ---
tab1, tab2 = st.tabs(["🏗️ Phase 1: Create & Print", "📊 Phase 2: Upload & Report"])

with tab1:
    st.header("Step 1: Generate Pen-Paper Test")
    if not db.empty:
        col1, col2 = st.columns(2)
        with col1:
            u_grade = st.selectbox("Select Grade", sorted(db['Grade'].unique()))
            sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
            u_subject = st.selectbox("Select Subject", sub_list)
        with col2:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Select Topic", topic_df['Chapter Name'].unique())
            u_num_q = st.number_input("Questions", 1, 10, 5)
            u_aid = st.text_input("Assessment ID (Unique)", value=f"{u_subject[:3].upper()}-101")

        if st.button("Generate Test & Excel Template"):
            u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
            with st.spinner("AI is engineering diagnostic questions..."):
                prompt = f"Create {u_num_q} conceptual MCQs for {u_grade} {u_subject} on {u_topic}. Outcomes: {u_outcomes}. Return JSON with 'questions' list: id, q, options (A,B,C,D), correct, and mappings (B,C,D misconceptions)."
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Output valid JSON only."}, {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                st.session_state[f"meta_{u_aid}"] = metadata
                st.success(f"Assessment {u_aid} Ready!")

                # 1. Provide Question Paper (Simple Text for now)
                st.write("### Preview Questions")
                for q in metadata['questions']:
                    st.write(f"**Q{q['id']}:** {q['q']}")

                # 2. Provide Template Excel
                template_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num_q)])
                template_df.loc[0] = ["Example: Rahul", "A", "B", "C", "D", "A"][:u_num_q+1]
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    template_df.to_excel(writer, index=False, sheet_name='Responses')
                st.download_button("📥 Download Excel Template", output.getvalue(), f"Template_{u_aid}.xlsx")

with tab2:
    st.header("Step 2: Upload Responses & Get Reports")
    target_aid = st.text_input("Enter Assessment ID to Link Metadata", value="")
    uploaded_file = st.file_uploader("Upload Filled Student Responses (Excel)", type=["xlsx"])

    if uploaded_file and target_aid:
        if f"meta_{target_aid}" not in st.session_state:
            st.error("Metadata not found. Did you generate this test in Phase 1?")
        else:
            responses_df = pd.read_excel(uploaded_file)
            meta = st.session_state[f"meta_{target_aid}"]
            
            st.subheader("📈 Classwise Misconception Report")
            
            # Logic to find common errors
            all_errors = []
            for index, row in responses_df.iterrows():
                for q in meta['questions']:
                    q_key = f"Q{q['id']}"
                    student_ans = row[q_key]
                    if student_ans != q['correct']:
                        error_type = q['mappings'].get(student_ans, "General Gap")
                        all_errors.append({"Student": row['Student Name'], "Topic": q_key, "Error": error_type})
            
            if all_errors:
                error_summary = pd.DataFrame(all_errors)
                st.write("**Top Misconceptions in Class:**")
                st.dataframe(error_summary['Error'].value_counts())
                
                st.divider()
                st.subheader("👤 Individual Remedial Plans")
                for student in responses_df['Student Name'].unique():
                    student_errors = error_summary[error_summary['Student'] == student]
                    with st.expander(f"Remedial Plan for {student}"):
                        if student_errors.empty:
                            st.success("Perfect Score! No remediation needed.")
                        else:
                            for _, err in student_errors.iterrows():
                                st.warning(f"**Issue:** {err['Error']}")
                                st.write("👉 *Action:* Teacher to re-explain this concept using visual aids.")
