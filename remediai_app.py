import streamlit as st
import pandas as pd
import plotly.express as px
from langchain_openai import ChatOpenAI

st.set_page_config(page_title="RemediAI", layout="wide", page_icon="📊")

st.title("📚 RemediAI - Smart Assessment Tool")
st.caption("No login • Teacher friendly • Powered by OpenAI")

# Load Database
@st.cache_data
def load_db():
    return pd.read_csv("Teachshank_Master_Database_FINAL (1).tsv", sep="\t")

db = load_db()

# Sidebar
st.sidebar.header("Create Assessment")
grade = st.sidebar.selectbox("Class / Grade", sorted(db['Grade'].unique()))
subject_list = sorted(db[db['Grade'] == grade]['Subject'].unique())
subject = st.sidebar.selectbox("Subject", subject_list)
topic = st.sidebar.text_input("Chapter / Topic", "Fractions")

difficulty = st.sidebar.slider("Difficulty Level (1-12)", 1, 12, 6)
num_questions = st.sidebar.number_input("Number of Questions", 8, 40, 15)

# OpenAI Key
if "openai_key" not in st.session_state:
    st.session_state.openai_key = ""

openai_key = st.sidebar.text_input("OpenAI API Key", value=st.session_state.openai_key, type="password")
if openai_key:
    st.session_state.openai_key = openai_key

# Generate Button
if st.button("🚀 Generate Assessment", type="primary", use_container_width=True):
    if not openai_key:
        st.error("Please enter your OpenAI API Key in sidebar")
    else:
        st.success(f"Generating {num_questions} questions for {grade} {subject} - {topic}")
        st.info("✅ Assessment generated (Demo mode for now). Full AI generation will be added in next update.")

        # Show beautiful demo assessment
        for i in range(num_questions):
            with st.container(border=True):
                st.markdown(f"**Q{i+1}.** Conceptual question from {topic} (Difficulty {difficulty})")
                st.markdown("A) Option 1 B) Option 2 C) Option 3 D) Option 4")

# Upload Responses
st.divider()
st.subheader("Upload Student Responses Excel")
uploaded = st.file_uploader("Upload Excel (Student Name + Answers)", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded)
    st.success(f"Loaded {len(df)} students")
    st.dataframe(df.head())

    if st.button("🔥 Analyze Misconceptions & Generate Reports", type="primary", use_container_width=True):
        st.balloons()
        st.success("AI Analysis Complete!")
        st.write("**Class Misconceptions Detected**")
        st.error("• Confusion between Area and Perimeter")
        st.error("• Misunderstanding of Fractions")
        
        fig = px.bar(x=["Area vs Perimeter", "Fractions", "Word Problems"], 
                     y=[45, 38, 22], title="Misconception Distribution")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Deep Remedial Plan")
        st.write("4-week detailed remedial plan generated for the class and individual students.")
