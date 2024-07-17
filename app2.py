import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI
 
load_dotenv()
client = OpenAI()
 
def extract_raw_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    raw_text = ""
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        raw_text += page.get_text("text")
    return raw_text
 
def extract_info_with_gpt(raw_text, prompt):
    completion = client.chat.completions.create(
                  model='gpt-4o',
                  temperature=0,
                  max_tokens=1500,
                  messages=[
                    {"role": "system", "content": "Extract the relevant information from the CV"},
                    {"role": "user", "content": prompt + "\n\n" + raw_text},
                ])
    
    response = completion.choices[0].message.content  
    return response.strip()
 
prompt = """
Please extract the following details from the CV:

Biography
Work Experience and Education
Total work experience duration
Total education duration
For each position or educational experience:
Job Title or Degree
Company or Institution
Dates (Start and End)
Description of responsibilities, achievements, or skills gained
Skills
Languages

The output must be in the following format:
{
    "name": "",
    "location": "",
    "biography": "",
    "totalWorkExperience": "",
    "totalEducationDuration": "",
    "workExperience": [
        {
            "jobTitle": "",
            "company": "",
            "period": "",
            "description": ""
        }
    ],
    "education": [
        {
            "degree": "",
            "educationalInstitution": "",
            "period": "",
            "description": ""
        }
    ],
    "skills": [],
    "languages": [
        {
            "name": "",
            "degree": ""  //options Beginner, Good, Fluent, Proficient, Native/Bilingual
        }
    ]
}

If something is not found, leave the field empty.
Instructions:
- name: First and Last name of the candidate
- location: City and State of the candidate
- biography: A brief description of the candidate
- totalWorkExperience: Total years and months of work experience
- totalEducationDuration: Total years of education
- workExperience: List of work experiences with job title, company, period, and description
- education: List of educational experiences with degree, educational institution, period, and description
- skills: List of skills (please provide only the skill names, e.g. Python, TensorFlow, etc., without any additional information e.g. CSS – basic knowledge should only be CSS)
- languages: List of languages with name and degree of proficiency (options: Beginner, Good, Fluent, Proficient, Native/Bilingual), example degree B2 is wrong, it should be Good.

Example:
{
    "name": "Marko Markovic",
    "location": "San Francisco, CA",
    "biography": "Marko is a data scientist with more than 5 years of experience in machine learning and natural language processing. He has a Ph.D. in computer science from Stanford University. He is proficient in Python, TensorFlow, and PyTorch. Marko is a native English speaker.",
    "totalWorkExperience": "5 years 3 months",
    "totalEducationDuration": "8 years",
    "workExperience": [
        {
            "jobTitle": "Data Scientist",
            "company": "CompanyA",
            "period": "Jan 2023 - ",
            "description": "Working as data scientist on NLP projects."
        },
        {
            "jobTitle": "Data Analyst",
            "company": "CompanyB",
            "period": "May 2019 - Jan 2023",
            "description": "Working as data analyst for financial reports."
        },
    ],
    "education": [
        {
            "degree": "Ph.D. in Computer Science",
            "educationalInstitution": "Stanford University",
            "period": "2013-2017",
            "description": ""
        },
        {
            "degree": "Msc. in Computer Science",
            "educationalInstitution": "Stanford University",
            "period": "2012-2013",
            "description": ""
        },
    ],
    "skills": ["Python", "TensorFlow", "PyTorch", "NLP", "Machine Learning", "Data Analysis", "OpenCV", "HuggingFace"],
    "languages": [
        {
            "name": "English",
            "degree": "Native/Bilingual"
        },
        {
            "name": "Spanish",
            "degree": "Proficient"
        },
        {
            "name": "Italian",
            "degree": "Beginner"
        },
    ]
}
"""
 
# Path to your CV PDF
pdf_path = "C:/Users/Talentwunder/Desktop/AI/ai-internal-cv2profile/resumes/cvjovanasekaric.pdf"
 
# Extract raw text from PDF
raw_text = extract_raw_text_from_pdf(pdf_path)
 
# Get the extracted information
extracted_info = extract_info_with_gpt(raw_text, prompt)
print(extracted_info)