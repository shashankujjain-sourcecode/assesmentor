import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re
from io import BytesIO

# --- 1. APP SETUP & STYLING ---
st.set_page_config(page_title="RemediAI: Master Diagnostic Suite", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #1e40af; color: white; font-weight: bold; height: 3.5em; }
    .report-card { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .remedial-box { background-color: #fef2f2; border-left: 5px solid #dc2626; padding: 15px; margin-top: 10px; }
    .metric-container { background-color: #eff6ff; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Add 'OPENAI_API_KEY' to Streamlit Secrets.")
    st.stop()

# --- 2. SMART DATABASE LOADING ---
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

# Initialize Session State for Memory & Metadata
if 'history' not in st.session_state: st.session_state['history'] = []
if 'meta_store' not in st.session_state: st.session_state['meta_store'] = {}

# --- 3. WORKFLOW TABS ---
tab1, tab2 = st.tabs(["🏗️ Phase 1: Assessment Creator", "📊 Phase 2: Diagnostic Reporting"])

with tab1:
    st.header("Step 1: Design Conceptual Assessment")
    if not db.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            u_grade = st.selectbox("Select Grade", sorted(db['Grade'].unique()))
            sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
            u_subject = st.selectbox("Select Subject", sub_list)
        with col2:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Select Topic/Chapter", topic_df['Chapter Name'].unique())
            u_diff = st.select_slider("Difficulty Level (1-12)", options=list(range(1, 13)), value=6)
        with col3:
            u_num_q = st.number_input("Number of Questions", 1, 15, 5)
            u_aid = st.text_input("Assessment ID", value=f"{u_subject[:3].upper()}-{u_grade[-1] if u_grade[-1].isdigit() else 'X'}-101")

        if st.button("Generate Paper & Diagnostic Key"):
            u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
            
            # Repetition check context
            avoid_list = ", ".join(st.session_state['history'][-10:]) 
            
            with st.spinner("AI is engineering diagnostic distractors..."):
                prompt = f"""
                Create {u_num_q} conceptual MCQs for {u_grade} {u_subject} on {u_topic}.
                Difficulty: {u_diff}/12. Outcomes: {u_outcomes}.
                
                STRICT RULES:
                1. NO diagrammatic, pictorial, or image-based questions. Text-only.
                2. NO repetition of these previous concepts: {avoid_list}.
                3. Stick strictly to the topic: {u_topic}.
                4. Every wrong option MUST map to a specific Indian student misconception.

                Return JSON only:
                {{
                  "questions": [
                    {{
                      "id": 1, "q": "...", "options": {{"A":"","B":"","C":"","D":""}}, "correct": "A",
                      "mappings": {{"B": "Misconception Name", "C": "Misconception Name", "D": "Logic Error"}},
                      "remedial_plan": "Specific activity to fix this error"
                    }}
                  ]
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                metadata = json.loads(response.choices[0].message.content)
                # Save to persistent storage for Phase 2
                st.session_state['meta_store'][u_aid] = metadata
                st.session_state['history'].append(u_topic)

                st.success(f"Assessment {u_aid} created and stored!")
                
                # Downloadable Excel Template
                tpl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num_q)])
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    tpl_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel Response Template", output.getvalue(), f"Template_{u_aid}.xlsx")

                # Print Preview
                for q in metadata['questions']:
                    st.write(f"**Q{q['id']}:** {q['q']}")

with tab2:
    st.header("Step 2: Upload Responses & Generate Deep Reports")
    input_aid = st.text_input("Enter Assessment ID to Link Metadata", placeholder="e.g. MAT-7-101")
    uploaded_file = st.file_uploader("Upload Completed Student Excel", type=["xlsx"])

    if uploaded_file and input_aid:
        if input_aid not in st.session_state['meta_store']:
            st.error("Metadata not found. Please ensure the ID matches Phase 1.")
        else:
            df = pd.read_excel(uploaded_file)
            meta = st.session_state['meta_store'][input_aid]
            
            # --- CLASSWISE REPORT ---
            st.subheader("📊 Class-Level Diagnostic")
            class_errors = []
            for _, row in df.iterrows():
                for q in meta['questions']:
                    ans = str(row[f"Q{q['id']}"]).strip().upper()
                    if ans != q['correct']:
                        class_errors.append(q['mappings'].get(ans, "Conceptual Gap"))
            
            if class_errors:
                err_counts = pd.Series(class_errors).value_counts()
                st.write("**Top Class-Wide Misconceptions:**")
                st.bar_chart(err_counts)
            
            st.divider()

            # --- INDIVIDUAL REPORT & REMEDIAL PLAN ---
            st.subheader("👤 Individual Student Diagnostic & Remedial Plan")
            student_name = st.selectbox("Select Student", df['Student Name'].unique())
            s_row = df[df['Student Name'] == student_name].iloc[0]
            
            for q in meta['questions']:
                s_ans = str(s_row[f"Q{q['id']}"]).strip().upper()
                with st.container():
                    if s_ans == q['correct']:
                        st.markdown(f"**Question {q['id']}:** ✅ Mastery Demonstrated")
                    else:
                        st.markdown(f"**Question {q['id']}:** ❌ Incorrect (Selected {s_ans})")
                        st.markdown(f"""
                        <div class="remedial-box">
                            <b>Detected Misconception:</b> {q['mappings'].get(s_ans, 'Conceptual Error')}<br><br>
                            <b>🛠️ Targeted Remedial Action:</b><br>{q['remedial_plan']}
                        </div>
                        """, unsafe_allow_html=True)
                st.write("")
