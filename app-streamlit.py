import re
from openai import OpenAI
import os
import streamlit as st
from dotenv import load_dotenv
import json
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional
import fitz
import streamlit as st

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not found.")
OpenAI.api_key = openai_api_key
client = OpenAI()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


class WorkExperience(BaseModel):
    jobTitle: Optional[str] = Field(None, alias='jobTitle')
    company: Optional[str] = Field(None, alias='company')
    period: Optional[str] = Field(None, alias='period')
    description: Optional[str] = Field(None, alias='description')

class Education(BaseModel):
    degree: Optional[str] = Field(None, alias='degree')
    educationalInstitution: Optional[str] = Field(None, alias='educationalInstitution')
    period: Optional[str] = Field(None, alias='period')
    description: Optional[str] = Field(None, alias='description')

class Language(BaseModel):
    name: Optional[str] = Field(None, alias='name')
    degree: Optional[str] = Field(None, alias='degree')

    @field_validator('degree')
    def validate_degree(cls, v):
        valid_degrees = ["Beginner", "Good", "Fluent", "Proficient", "Native/Bilingual"]
        if v not in valid_degrees:
            raise ValueError(f'Degree must be one of {valid_degrees}')
        return v

class UserProfile(BaseModel):
    name: Optional[str] = Field(None, alias='name')
    location: Optional[str] = Field(None, alias='location')
    biography: Optional[str] = Field(None, alias='biography')
    totalWorkExperience: Optional[str] = Field(None, alias='totalWorkExperience')
    totalEducationDuration: Optional[str] = Field(None, alias='totalEducationDuration')
    workExperience: List[WorkExperience] = Field(default_factory=list, alias='workExperience')
    education: List[Education] = Field(default_factory=list, alias='education')
    skills: List[str] = Field(default_factory=list, alias='skills')
    languages: List[Language] = Field(default_factory=list, alias='languages')

def extract_json_from_string(input_string: str) -> dict:
    try:
        json_str = re.search(r'{.*}', input_string, re.DOTALL).group()
        return json.loads(json_str)
    except (AttributeError, json.JSONDecodeError):
        print("No valid JSON found in the input string.")
        return {}

def parse_user_profile(input_string: str) -> Optional[UserProfile]:
    data = extract_json_from_string(input_string)
    if not data:
        return None
    try:
        cleaned_data = {
            "name": data.get("name", ""),
            "location": data.get("location", ""),
            "biography": data.get("biography", ""),
            "totalWorkExperience": data.get("totalWorkExperience", ""),
            "totalEducationDuration": data.get("totalEducationDuration", ""),
            "workExperience": [
                {
                    "jobTitle": we.get("jobTitle", ""),
                    "company": we.get("company", ""),
                    "period": we.get("period", ""),
                    "description": we.get("description", "")
                } for we in data.get("workExperience", [])
            ],
            "education": [
                {
                    "degree": ed.get("degree", ""),
                    "educationalInstitution": ed.get("educationalInstitution", ""),
                    "period": ed.get("period", ""),
                    "description": ed.get("description", "")
                } for ed in data.get("education", [])
            ],
            "skills": data.get("skills", []),
            "languages": [
                {
                    "name": lang.get("name", ""),
                    "degree": lang.get("degree", "")
                } for lang in data.get("languages", [])
            ]
        }

        user_profile = UserProfile(**cleaned_data)
        return user_profile
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None


def extract_raw_text_from_pdf(pdf_file):
    document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    raw_text = ""
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        raw_text += page.get_text("text")
    return raw_text
 
def extract_info_with_gpt(raw_text, prompt):
    completion = client.chat.completions.create(
                  model='gpt-4o',
                  temperature=0,
                  response_format={ "type": "json_object" },
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

The output must be in the following JSON format:
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


def check_credentials(username, password):
    correct_password = os.getenv('USER_PASSWORD')
    return username == "talentwunder" and password == correct_password

def display_login_form():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")
        if login_button:
            if check_credentials(username, password):
                st.session_state['logged_in'] = True
                st.success("Logged in successfully.")
                # Using st.experimental_rerun() to force the app to rerun might help, but use it judiciously.
                st.experimental_rerun()
            else:
                st.error("Incorrect username or password.")


def display_main_app():
    st.title('CV2Profile Convertor')
    uploaded_file = st.file_uploader('Choose CV to upload', type="pdf")
 
    if st.button('Convert CV'):
        if uploaded_file:
            with st.spinner('Converting... Please wait'):
                raw_text = extract_raw_text_from_pdf(uploaded_file)
                extracted_info = extract_info_with_gpt(raw_text, prompt)
                parsed_profile = parse_user_profile(extracted_info)
                if parsed_profile:
                    # st.write(parsed_profile.model_dump_json(indent=2))
                    if parsed_profile.name:
                        st.header(parsed_profile.name)

                    if parsed_profile.location:
                        st.subheader(f"Location: {parsed_profile.location}")

                    if parsed_profile.biography:
                        st.markdown(f"**Biography:** {parsed_profile.biography}")

                    if parsed_profile.totalWorkExperience:
                        st.markdown(f"**Total Work Experience:** {parsed_profile.totalWorkExperience}")

                    if parsed_profile.totalEducationDuration:
                        st.markdown(f"**Total Education Duration:** {parsed_profile.totalEducationDuration}")

                    st.markdown("### Work Experience")
                    for work in parsed_profile.workExperience:
                        with st.expander(f"{work.jobTitle} at {work.company} ({work.period})"):
                            st.markdown(work.description)

                    st.markdown("### Education")
                    for edu in parsed_profile.education:
                        with st.expander(f"{edu.degree} at {edu.educationalInstitution} ({edu.period})"):
                            st.markdown(edu.description)

                    st.markdown("### Skills")
                    st.write(", ".join(parsed_profile.skills))

                    st.markdown("### Languages")
                    for lang in parsed_profile.languages:
                        st.markdown(f"- **{lang.name}:** {lang.degree}")
                else:
                    st.write("Failed to parse the user profile.")
                
 
if not st.session_state['logged_in']:
    display_login_form()
else:
    display_main_app()