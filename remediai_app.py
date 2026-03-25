import google.generativeai as genai
import pandas as pd
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- USER ADDS KEY HERE ---
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

class MisconceptionEngine:
    def __init__(self):
        self.keys_dir = "metadata_library"
        self.output_dir = "generated_reports"
        os.makedirs(self.keys_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def create_assessment(self, aid, grade, subject, topic):
        """Generates the test and saves the Misconception Map JSON"""
        prompt = f"Create a 5-question MCQ for Grade {grade} {subject} on {topic}. " \
                 "Each wrong option must map to a specific logic error. Return VALID JSON ONLY."
        
        response = model.generate_content(prompt)
        # Clean and save the 'Brain' of the assessment
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        
        with open(f"{self.keys_dir}/{aid}.json", "w") as f:
            json.dump(data, f)
        print(f"Success! Assessment {aid} created. Ensure B1 in Excel matches this ID.")

    def process_excel(self, file_path):
        """Reads ID from Excel B1, matches the key, and generates report"""
        # Read the ID from Cell B1 (row 0, column 1)
        id_df = pd.read_excel(file_path, header=None, nrows=1)
        assessment_id = str(id_df.iloc[0, 1]).strip()
        
        # Read the actual data starting from Row 3 (header is row 2)
        data_df = pd.read_excel(file_path, skiprows=2)
        
        # Load the Key
        key_path = f"{self.keys_dir}/{assessment_id}.json"
        if not os.path.exists(key_path):
            print(f"Error: No metadata found for ID: {assessment_id}")
            return

        with open(key_path, "r") as f:
            metadata = json.load(f)

        self._generate_diagnostic_pdf(assessment_id, data_df, metadata)

    def _generate_diagnostic_pdf(self, aid, df, metadata):
        """Creates the 3-part report better than Ei ASSET"""
        pdf_path = f"{self.output_dir}/Report_{aid}.pdf"
        c = canvas.Canvas(pdf_path, pagesize=A4)
        
        # Logic to calculate scores and aggregate misconceptions
        # [This part uses the 'mappings' from metadata to find errors]
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 800, f"Diagnostic Insight: {aid}")
        
        # Add deep remedial plan using Gemini based on the top class error
        # ... (PDF generation logic) ...
        
        c.save()
        print(f"Report generated: {pdf_path}")

# --- EXAMPLE USAGE ---
engine = MisconceptionEngine()

# Step 1: Create a test (Do this once per topic)
# engine.create_assessment("MATH-701", 7, "Math", "Percentage & Profit")

# Step 2: Process the filled Excel (The script finds the ID automatically)
# engine.process_excel("path_to_your_filled_excel.xlsx")
