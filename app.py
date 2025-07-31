from flask import Flask, render_template, request, send_file
import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util
import pandas as pd
from io import BytesIO
import spacy
from rapidfuzz import fuzz
import re

# === Setup ===
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

SKILL_KEYWORDS = {
    'python', 'machine learning', 'sql', 'data science', 'pandas',
    'tensorflow', 'keras', 'numpy', 'scikit-learn', 'deep learning',
    'java', 'c++', 'excel', 'power bi', 'tableau', 'nlp'
}

# === Helper Functions ===
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])

def normalize_score(raw_score, max_possible=0.6):
    clamped = max(0.0, min(raw_score, max_possible))
    return round((clamped / max_possible) * 10, 2)

def score_with_ai(text, job_description):
    embeddings = model.encode([text, job_description], convert_to_tensor=True)
    raw_score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return normalize_score(raw_score)

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
    found = []
    for skill in SKILL_KEYWORDS:
        if fuzz.partial_ratio(skill.lower(), text.lower()) > 85:
            found.append(skill)
    return ', '.join(found) if found else 'Not found'

def extract_experience(text):
    return '1+ Internship' if re.search(r'\bintern(ship)?\b', text, re.IGNORECASE) else 'No Internship'

def extract_named_entities(text):
    doc = nlp(text)
    entities = {
        "PERSON": [],
        "ORG": [],
        "GPE": [],
        "EMAIL": [],
        "PHONE": []
    }

    for ent in doc.ents:
        if ent.label_ in entities:
            entities[ent.label_].append(ent.text)

    # Regex email/phone extraction
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    phones = re.findall(r'(\+?\d[\d\s\-().]{7,}\d)', text)

    entities['EMAIL'] = list(set(entities['EMAIL'] + emails))
    entities['PHONE'] = list(set(entities['PHONE'] + phones))

    return entities

def skill_match_score(resume_skills, required_skills):
    resume_set = set([s.strip().lower() for s in resume_skills.split(',') if s.strip()])
    required_set = set([s.strip().lower() for s in required_skills])
    if not resume_set or not required_set:
        return 0
    match_count = len(resume_set & required_set)
    return match_count / len(required_set)

# === Routes ===
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

        # Extract skill keywords from job description for scoring
        job_keywords = extract_skills(job_description)
        job_skill_list = [k.strip() for k in job_keywords.split(',')] if job_keywords != 'Not found' else []

        for file in files:
            if file and file.filename.lower().endswith('.pdf'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                text = extract_text_from_pdf(filepath)
                ai_score = score_with_ai(text, job_description)

                cgpa = extract_cgpa(text)
                skills = extract_skills(text)
                experience = extract_experience(text)
                ner_entities = extract_named_entities(text)

                # Add skill-based bonus
                skill_bonus = skill_match_score(skills, job_skill_list) * 2  # weighted out of 2
                final_score = min(ai_score + skill_bonus, 10)

                status = 'shortlisted' if final_score > 7 else 'review'

                results.append({
                    'name': file.filename,
                    'score': round(final_score, 2),
                    'cgpa': cgpa,
                    'skills': skills,
                    'experience': experience,
                    'status': status,
                    'entities': ner_entities
                })

        results = sorted(results, key=lambda x: x['score'], reverse=True)

    return render_template('index.html', results=results, job_description=job_description, error=error)

@app.route('/export_excel')
def export_excel():
    global results
    if not results:
        return "No results to export", 400

    df = pd.DataFrame(results)
    df.rename(columns={
        'name': 'Candidate Name',
        'score': 'Match Score',
        'cgpa': 'CGPA',
        'skills': 'Skills',
        'experience': 'Experience',
        'status': 'Status'
    }, inplace=True)

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

import os
print("PORT environment variable is:", os.environ.get("PORT"))
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
