from flask import Flask, render_template, request
import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util
# added Export results as Excel
import pandas as pd
from io import BytesIO
from flask import send_file


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Example job description
#JOB_DESCRIPTION = """
#We are looking for candidates with strong skills in Python, Machine Learning, and Data Science. 
#Preference will be given to those who have done internships and have a high CGPA.
#"""

# added --> begin

import re

# Define a basic skill set to match against
SKILL_KEYWORDS = {
    'python', 'machine learning', 'sql', 'data science', 'pandas',
    'tensorflow', 'keras', 'numpy', 'scikit-learn', 'deep learning',
    'java', 'c++', 'excel', 'power bi', 'tableau', 'nlp'
}

def extract_cgpa(text):
    patterns = [
        r'(?:CGPA|GPA)[\s:]*([0-9]\.\d{1,2})',
        r'([0-9]\.\d{1,2})\s*/\s*10'
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return 'Not found'


def extract_skills(text):
    found = [skill for skill in SKILL_KEYWORDS if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE)]
    return ', '.join(found) if found else 'Not found'

def extract_experience(text):
    if re.search(r'\bintern(ship)?\b', text, re.IGNORECASE):
        return '1+ Internship'
    return 'No Internship'

# added -- end

def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text

def score_with_ai(text, job_description):
    # Encode resume and job description
    embeddings = model.encode([text, job_description], convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return float(similarity[0][0]) * 10  # Convert similarity to 0-10 score

@app.route('/', methods=['GET', 'POST'])
def index():
    global results
    results = []

    job_description = ""
    error = None

    if request.method == 'POST':
        job_description = request.form.get('job_description')
        files = request.files.getlist('resumes')

        if not job_description or not files or all(f.filename == '' for f in files):
            error = "Please provide a job description and upload at least one resume (PDF)."
            return render_template('index.html', results=[], job_description=job_description, error=error)

        for file in files:
            if file and file.filename.lower().endswith('.pdf'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                text = extract_text_from_pdf(filepath)
                #ai_score = score_with_ai(text, job_description)
                # the above line produced a bug in the template index.html filling the score bar full
                # when results were negative i.e. (-) cosine similarity
                # so we are clamping the score between 0 and 10

                raw_score = score_with_ai(text, job_description)
                ai_score = max(0, min(round(raw_score, 2), 10))  # Clamp score between 0 and 10


                cgpa = extract_cgpa(text)
                skills = extract_skills(text)
                experience = extract_experience(text)

                status = 'shortlisted' if ai_score > 7 else 'review'

                results.append({
                    'name': file.filename,
                    'score': round(ai_score, 2),
                    'cgpa': cgpa,
                    'skills': skills,
                    'experience': experience,
                    'status': status
                })

        results = sorted(results, key=lambda x: x['score'], reverse=True)

    return render_template('index.html', results=results, job_description=job_description, error=error)



# export results as Excel --> begin
results = []
@app.route('/export_excel')
def export_excel():
    # Example: assume you have 'results' stored or recreate them here.
    # For demo, let's hardcode or reuse your existing scoring logic.
    # In real app, you'd persist results or regenerate them on export.

    # For now, let's just re-run the existing example JOB_DESCRIPTION scoring 
    # on files in uploads folder (or better, persist results after upload).

    # For demo, let's just create a dummy dataframe from last processed results
    # You can modify this to fetch real data from your DB or session

    # Suppose you keep last results in a global variable (not ideal but simple)
    global results
    if not results:
        return "No results to export", 400

    df = pd.DataFrame(results)
    # Rename columns for nicer Excel headers
    df.rename(columns={
        'name': 'Candidate Name',
        'score': 'Match Score',
        'cgpa': 'CGPA',
        'skills': 'Skills',
        'experience': 'Experience',
        'status': 'Status'
    }, inplace=True)

    # Create an in-memory Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Screening Results')

    output.seek(0)

    return send_file(
        output,
        download_name="screening_results.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# excel --> end

if __name__ == '__main__':
    app.run(debug=True)
