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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse, urlunparse

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not found.")
OpenAI.api_key = openai_api_key
client = OpenAI()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    
    

def fix_url(url):
    parsed_url = urlparse(url)
    
    if not parsed_url.scheme:
        url = 'https://' + url
        parsed_url = urlparse(url)
    
    return urlunparse(parsed_url)
    
    

class TotalExperience(BaseModel):
    totalWorkExperience: Optional[str] = Field(None, alias='totalWorkExperience')
    totalEducationDuration: Optional[str] = Field(None, alias='totalEducationDuration')

    @field_validator('totalWorkExperience')
    def validate_totalWorkExperience(cls, v):
        if not v:
            return ''
        return v

    @field_validator('totalEducationDuration')
    def validate_totalEducationDuration(cls, v):
        if not v:
            return ''
        return v


class WorkExperience(BaseModel):
    jobTitle: Optional[str] = Field(None, alias='jobTitle')
    company: Optional[str] = Field(None, alias='company')
    period: Optional[str] = Field(None, alias='period')
    periodStart: Optional[str] = Field(None, alias='periodStart')
    periodEnd: Optional[str] = Field(None, alias='periodEnd')
    totalLength: Optional[str] = Field(None, alias='totalLength')
    description: Optional[str] = Field(None, alias='description')

class Education(BaseModel):
    degree: Optional[str] = Field(None, alias='degree')
    educationalInstitution: Optional[str] = Field(None, alias='educationalInstitution')
    period: Optional[str] = Field(None, alias='period')
    periodStart: Optional[str] = Field(None, alias='periodStart')
    periodEnd: Optional[str] = Field(None, alias='periodEnd')
    totalLength: Optional[str] = Field(None, alias='totalLength')
    description: Optional[str] = Field(None, alias='description')

class Language(BaseModel):
    name: Optional[str] = Field(None, alias='name')
    degree: Optional[str] = Field(None, alias='degree')

    @field_validator('degree')
    def validate_degree(cls, v):
        valid_degrees = ["Beginner", "Good", "Fluent", "Proficient", "Native/Bilingual", ""]
        if v not in valid_degrees:
            return ''
        return v
    
class Publication(BaseModel):
    date: Optional[str] = Field(None, alias='date')
    description: Optional[str] = Field(None, alias='description')
    name: Optional[str] = Field(None, alias='name')
    periodEnd: Optional[str] = Field(None, alias='periodEnd')
    periodStart: Optional[str] = Field(None, alias='periodStart')
    publisher: Optional[str] = Field(None, alias='publisher')
    tags: Optional[List[str]] = Field(None, alias='tags')
    url: Optional[str] = Field(None, alias='url')
    
class Project(BaseModel):
    date: Optional[str] = Field(None, alias='date')
    description: Optional[str] = Field(None, alias='description')
    name: Optional[str] = Field(None, alias='name')
    periodEnd: Optional[str] = Field(None, alias='periodEnd')
    periodStart: Optional[str] = Field(None, alias='periodStart')
    skills: Optional[List[str]] = Field(None, alias='skills')
    url: Optional[str] = Field(None, alias='url')

class UserProfile(BaseModel):
    name: Optional[str] = Field(None, alias='name')
    emails: Optional[List[str]] = Field(None, alias='emails')
    phones: Optional[List[str]] = Field(None, alias='phones')
    links: Optional[List[str]] = Field(None, alias='links')
    location: Optional[str] = Field(None, alias='location')
    biography: Optional[str] = Field(None, alias='biography')
    totalWorkExperience: Optional[str] = Field(None, alias='totalWorkExperience')
    totalEducationDuration: Optional[str] = Field(None, alias='totalEducationDuration')
    workExperience: List[WorkExperience] = Field(default_factory=list, alias='workExperience')
    education: List[Education] = Field(default_factory=list, alias='education')
    skills: List[str] = Field(default_factory=list, alias='skills')
    languages: List[Language] = Field(default_factory=list, alias='languages')
    publications: List[Publication] = Field(default_factory=list, alias='publications')
    projects: List[Project] = Field(default_factory=list, alias='projects')

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
            "emails": data.get("emails", []),
            "phones": data.get("phones", []),
            "links": [fix_url(link) for link in data.get("links", [])],
            "location": data.get("location", ""),
            "biography": data.get("biography", ""),
            "totalWorkExperience": data.get("totalWorkExperience", ""),
            "totalEducationDuration": data.get("totalEducationDuration", ""),
            "workExperience": [
                {
                    "jobTitle": we.get("jobTitle", ""),
                    "company": we.get("company", ""),
                    "period": we.get("period", ""),
                    "periodStart": we.get("periodStart", ""),
                    "periodEnd": we.get("periodEnd", ""),
                    "totalLength": we.get("totalLength", ""),
                    "description": we.get("description", "")
                } for we in data.get("workExperience", [])
            ],
            "education": [
                {
                    "degree": ed.get("degree", ""),
                    "educationalInstitution": ed.get("educationalInstitution", ""),
                    "period": ed.get("period", ""),
                    "periodStart": ed.get("periodStart", ""),
                    "periodEnd": ed.get("periodEnd", ""),
                    "totalLength": ed.get("totalLength", ""),
                    "description": ed.get("description", "")
                } for ed in data.get("education", [])
            ],
            "skills": data.get("skills", []),
            "languages": [
                {
                    "name": lang.get("name", ""),
                    "degree": lang.get("degree", "")
                } for lang in data.get("languages", [])
            ],
            "publications": [
                {
                    "date": pub.get("date", ""),
                    "description": pub.get("description", ""),
                    "name": pub.get("name", ""),
                    "periodEnd": pub.get("periodEnd", ""),
                    "periodStart": pub.get("periodStart", ""),
                    "publisher": pub.get("publisher", ""),
                    "tags": pub.get("tags", []),
                    "url": pub.get("url", "")
                } for pub in data.get("publications", [])
            ],
            "projects": [
                {
                    "date": proj.get("date", ""),
                    "description": proj.get("description", ""),
                    "name": proj.get("name", ""),
                    "periodEnd": proj.get("periodEnd", ""),
                    "periodStart": proj.get("periodStart", ""),
                    "skills": proj.get("skills", []),
                    "url": proj.get("url", "")
                } for proj in data.get("projects", [])
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
        links = page.get_links()
        for link in links:
            if link["kind"] == fitz.LINK_URI:  # Check if the link is a URL
                url = link['uri']
                raw_text += '\n' + url
    return raw_text
 
def extract_info_with_gpt(raw_text, prompt):
    cv_prompt = prompt.replace("{DATETIME}", datetime.now().strftime("%Y-%m-%d")) + "\n\n" + raw_text
    # print(cv_prompt)
    completion = client.chat.completions.create(
                  model='gpt-4o',
                  temperature=0,
                  response_format={ "type": "json_object" },
                  messages=[
                    {"role": "system", "content": "Extract the relevant information from the CV"},
                    {"role": "user", "content": cv_prompt },
                ])
    
    response = completion.choices[0].message.content 
    # print(response) 
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
Total Length (years and months) # This is the total years and months of work experience for that position or educational degree. Please evaluate the total length based on the provided periods.
Description of responsibilities, achievements, or skills gained
Skills
Languages
Publications
Projects

The output must be in the following JSON format:
{
    "name": "",
    "emails": [],
    "phones": [],
    "links": [],
    "location": "",
    "biography": "",
    "totalWorkExperience": "",
    "totalEducationDuration": "",
    "workExperience": [
        {
            "jobTitle": "",
            "company": "",
            "period": "",
            "periodStart": "",
            "periodEnd": "",
            "totalLength": "",   //total years and months of work experience for that position. Please, calculate it correctly. If the end date is not provided, assume it is the current date {DATETIME}. If the month is not provided, assume it is January for start dates and December for end dates. If it is from Jan 22 to Jan 23, then it is 13 months. Include the last month if it is not full.
            "description": ""
        }
    ],
    "education": [
        {
            "degree": "",
            "educationalInstitution": "",
            "period": "",
            "periodStart": "",
            "periodEnd": "",
            "totalLength": "",    //total years and months of studies for that educational degree. Please, calculate it correctly. If the end date is not provided, assume it is the current date {DATETIME}. If the month is not provided, assume it is January for start dates and December for end dates. If it is from Jan 22 to Jan 23, then it is 13 months. Include the last month if it is not full.
            "description": ""
        }
    ],
    "skills": [],
    "languages": [
        {
            "name": "",
            "degree": ""  //options Beginner, Good, Fluent, Proficient, Native/Bilingual
        }
    ],
    "publications": [
        {
            "date": "",
            "description": "",
            "name": "",
            "periodEnd": "",
            "periodStart": "",
            "publisher": "",
            "tags": [],
            "url": ""
        }
    ],
    "projects": [
        {
            "date": "",
            "description": "",
            "name": "",
            "periodEnd": "",
            "periodStart": "",
            "skills": [],
            "url": ""
        }
    ]
}

If something is not found, leave the field empty.
Instructions:
- name: First and Last name of the candidate
- emails: List of email addresses of user
- phones: List of phone numbers of user
- links: List of links to user's profiles (e.g. LinkedIn, GitHub, Xing, Kaggle, etc.). If there are multiple links, from other sections, like Projects, Publications, please DO NOT include them here!
- location: City and State of the candidate, please provide it only from biography or data where it is clearly stated, DO NOT EXTRACT IT FROM POSITION OR EDUCATION
- biography: A brief description of the candidate
- totalWorkExperience: Total years and months of work experience
- totalEducationDuration: Total years of education
- workExperience: List of work experiences with job title, company, period, totalLength (total years and months of work experience for that position) and description
- education: List of educational experiences with degree, educational institution, period, totalLength (total years and months of studies for that educational degree) and description
- skills: List of skills (please provide only the skill names, e.g. Python, TensorFlow, etc., without any additional information e.g. CSS – basic knowledge should only be CSS)
- languages: List of languages with name and degree of proficiency (options: Beginner, Good, Fluent, Proficient, Native/Bilingual), example degree B2 is wrong, it should be Good.
- publications: List of publications (books, scientific papers, etc.) with date, description, name, periodEnd, periodStart, publisher, tags, and url
- projects: List of projects (that don't belong to the working experience) with date, description, name, periodEnd, periodStart, skills, and url

Example:
{
    "name": "Marko Markovic",
    "emails": ['marko.markovic@gmail.com'],
    "phones": ['123-456-7890'],
    "links": ['https://www.linkedin.com/in/marko-markovic'],
    "location": "San Francisco, CA",
    "biography": "Marko is a data scientist with more than 5 years of experience in machine learning and natural language processing. He has a Ph.D. in computer science from Stanford University. He is proficient in Python, TensorFlow, and PyTorch. Marko is a native English speaker.",
    "totalWorkExperience": "5 years 3 months",
    "totalEducationDuration": "8 years",
    "workExperience": [
        {
            "jobTitle": "Data Scientist",
            "company": "CompanyA",
            "period": "Jan 2023 - ",
            "periodStart": "01-01-2023",
            "periodEnd": "",
            "totalLength": "1 year, 7 months",
            "description": "Working as data scientist on NLP projects."
        },
        {
            "jobTitle": "Data Analyst",
            "company": "CompanyB",
            "period": "May 2019 - Jan 2023",
            "periodStart": "01-05-2019",
            "periodEnd": "31-01-2023",
            "totalLength": "3 years, 9 months",
            "description": "Working as data analyst for financial reports."
        },
    ],
    "education": [
        {
            "degree": "Ph.D. in Computer Science",
            "educationalInstitution": "Stanford University",
            "period": "2013-2017",
            "periodStart": "01-01-2013",
            "periodEnd": "31-12-2017",
            "totalLength": "4 years",
            "description": ""
        },
        {
            "degree": "Msc. in Computer Science",
            "educationalInstitution": "Stanford University",
            "period": "2012-2013",
            "periodStart": "01-01-2012",
            "periodEnd": "31-12-2013",
            "totalLength": "2 years",
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
    ],
    "publications": [
        {
            "date": "2022-01-01",
            "description": "Published a paper on machine learning.",
            "name": "Machine Learning Paper",
            "periodEnd": "2022",
            "periodStart": "2021",
            "publisher": "IEEE",
            "tags": ["Machine Learning", "NLP"],
            "url": "https://www.example.com/paper"
        }
    ],
    "projects": [
        {
            "date": "2022-01-01",
            "description": "Built a chatbot for customer service.",
            "name": "Customer Service Chatbot",
            "periodEnd": "2022",
            "periodStart": "2021",
            "skills": ["Python", "TensorFlow", "NLP"],
            "url": "https://www.example.com/chatbot"
        }
    ]
}

Please, make sure to provide all the requested information and that each Work Experience, Education, publication, and project are EXTRACTED from uploaded resume.
For calculating dates, keep in mind that today it is: {DATETIME}
Please, provide correct length of work experience and education duration for each position based on the provided periods and provided current date.

Please, make sure that you know difference between EDUCATION and WORK EXPERIENCE. It is very important to split them correctly!


IMPORTANT:
WHEN CALCULATING TOTALLENGTH FOR SPECIFIC POSITION OR EDUCATION, PLEASE, INCLUDE THE LAST MONTH IF IT IS NOT FULL. 
EXAMPLE: FEB 2022 - FEB 2023 IS 13 MONTHS, NOT 12 (1 YEAR), SO SOLUTION IS 1 YEAR 1 MONTH, NOT 1 YEAR!
EXAMPLE 2: 2018 - 2019 IS 2 YEARS, NOT 1 YEAR!
EXAMPLE 3: JAN 2022 - FEB 2023 IS 14 MONTHS (1 YEAR 2 MONTHS), NOT 1 YEAR 1 MONTH!

Check the examples above and make sure to calculate it correctly! Do not make mistakes!
"""

system_prompt_duration_length = """
Please calculate the total work experience duration and total education duration based on the user's provided periods. Follow these instructions carefully:

1. **Work Experience Calculation**:
   - Calculate the total years and months of work experience based on the provided periods.
   - If there is a gap between two periods, do not count that time.
   - If there is an overlap between two periods, count the overlapping time only once.
   - If the end date is not provided, assume it is the current date.
   - If the month is not provided, assume it is January for start dates and December for end dates.
   - After calculating, store the total work experience duration.

2. **Education Duration Calculation**:
   - Separately, calculate the total years and months of education based on the provided periods.
   - Apply the same rules as above: do not count gaps, and count overlapping time only once.
   - If the end date is not provided, assume it is the current date.
   - If the month is not provided, assume it is January for start dates and December for end dates.
   - After calculating, store the total education duration.

3. **Output**:
   - The output must be in the following JSON format:
     ```json
     {
         "totalWorkExperience": "X years Y months",
         "totalEducationDuration": "X years Y months"
     }
     ```
   - Ensure that the work experience and education durations are calculated and stored separately before outputting the final JSON.

The current date is {DATETIME}.
The user's work experience is {WORK_EXPERIENCE}.
The user's education experience is {EDUCATION}.

Example:
The current date is 2024-08-26.
The user's work experience is ['Jan 2024 - NOW', 'July 2022 - Jan 2024', 'Jan 2021 - July 2022', 'Jan 2020 - Jan 2021', 'Jan 2019 - July 2021']
The user's education experience is ['2019 - ', '2017 - 2018', '2014 - 2017']

The output MUST be:
{
    "totalWorkExperience": "5 years 8 months",
    "totalEducationDuration": "9 years 8 months"
}
"""


def calculate_years_months(date1, date2):

    d1 = datetime.strptime(date1, "%d-%m-%Y")
    
    if date2 == "":
        d2 = datetime.now()
    else:
        d2 = datetime.strptime(date2, "%d-%m-%Y")
    
    years = d2.year - d1.year
    months = d2.month - d1.month
    
    if d2.day >= d1.day:
        months += 1
    
    if months >= 12:
        years += 1
        months -= 12
        
    if months < 0:
        years -= 1
        months += 12
    
    return years, months


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
                    working_experience, education_experience = [], []
                    if parsed_profile.name:
                        st.header(parsed_profile.name)

                    if parsed_profile.location:
                        st.subheader(f"Location: {parsed_profile.location}")
                        
                    if parsed_profile.emails:
                        st.markdown(f"**Emails:** {', '.join(parsed_profile.emails)}")
                        
                    if parsed_profile.phones:
                        st.markdown(f"**Phones:** {', '.join(parsed_profile.phones)}")
                        
                    if parsed_profile.links:
                        st.markdown(f"**Links:** {', '.join(parsed_profile.links)}")

                    if parsed_profile.biography:
                        st.markdown(f"**Biography:** {parsed_profile.biography}")

                    st.markdown("### Work Experience")
                    for work in parsed_profile.workExperience:
                        working_experience.append(work.period)
                        years, months = calculate_years_months(work.periodStart, work.periodEnd)
                        duration_str = ""
                        if years > 0:
                            duration_str += f"{years} year{'s' if years != 1 else ''}"
                        if months > 0:
                            if duration_str:
                                duration_str += " "
                            duration_str += f"{months} month{'s' if months != 1 else ''}"
                        with st.expander(f"{work.jobTitle} at {work.company} ({work.period} : {duration_str})"):
                            st.markdown(work.description)
                
                        
                    st.markdown("### Education")
                    for edu in parsed_profile.education:
                        education_experience.append(edu.period)
                        years, months = calculate_years_months(edu.periodStart, edu.periodEnd)
                        duration_str = ""
                        if years > 0:
                            duration_str += f"{years} year{'s' if years != 1 else ''}"
                        if months > 0:
                            if duration_str:
                                duration_str += " "
                            duration_str += f"{months} month{'s' if months != 1 else ''}"
                        with st.expander(f"{edu.degree} at {edu.educationalInstitution} ({edu.period} : {duration_str})"):
                            st.markdown(edu.description)
                            
                        
                    total_experience = extract_total_length_with_gpt(str(working_experience), str(education_experience), system_prompt_duration_length)
                    
                    if working_experience:
                        st.markdown(f"**Total Work Experience:** {total_experience.totalWorkExperience}")
                    
                    if education_experience:
                        st.markdown(f"**Total Education Duration:** {total_experience.totalEducationDuration}")

                    st.markdown("### Skills")
                    st.write(", ".join(parsed_profile.skills))

                    st.markdown("### Languages")
                    for lang in parsed_profile.languages:
                        st.markdown(f"- **{lang.name}:** {lang.degree}")  
                        
                    st.markdown("### Publications")
                    for pub in parsed_profile.publications:
                        with st.expander(f"{pub.name} ({pub.periodStart} - {pub.periodEnd})"):
                            st.markdown(f"**Date:** {pub.date}")
                            st.markdown(f"**Publisher:** {pub.publisher}")
                            st.markdown(f"**Description:** {pub.description}")
                            st.markdown(f"**Tags:** {', '.join(pub.tags)}")
                            st.markdown(f"**URL:** {pub.url}")
                            
                    st.markdown("### Projects")
                    for proj in parsed_profile.projects:
                        with st.expander(f"{proj.name} ({proj.periodStart} - {proj.periodEnd})"):
                            st.markdown(f"**Date:** {proj.date}")
                            st.markdown(f"**Description:** {proj.description}")
                            st.markdown(f"**Skills:** {', '.join(proj.skills)}")
                            st.markdown(f"**URL:** {proj.url}")
                else:
                    st.write("Failed to parse the user profile.")
                    
                    
def extract_total_length_with_gpt(working_experience, education, prompt):
    prompt = prompt.replace("{DATETIME}", datetime.now().strftime("%Y-%m-%d")).replace("{WORK_EXPERIENCE}", working_experience).replace("{EDUCATION}", education)
    completion = client.chat.completions.create(
                  model='gpt-4o',
                  temperature=0,
                  response_format={ "type": "json_object" },
                  messages=[
                    {"role": "system", "content": "Extract the relevant information from the provided periods"},
                    {"role": "user", "content": prompt},
                ])
    
    response = completion.choices[0].message.content 
    # print(response)
    data = extract_json_from_string(response)
    if not data:
        return None
    try:
        cleaned_data = {
            "totalWorkExperience": data.get("totalWorkExperience", ""),
            "totalEducationDuration": data.get("totalEducationDuration", "")
        }
        total_length = TotalExperience(**cleaned_data)
        return total_length
    except ValidationError as e:
        return None
                
 
if not st.session_state['logged_in']:
    display_login_form()
else:
    display_main_app()
