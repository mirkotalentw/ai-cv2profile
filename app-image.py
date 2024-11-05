import re
from openai import OpenAI
import os
import streamlit as st
from dotenv import load_dotenv
import json
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional
import fitz  # PyMuPDF
import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse, urlunparse
import base64
from pdf2image import convert_from_bytes
import io
import tempfile
import os
from PIL import Image
from io import BytesIO

def encode_image(image_bytes_io):
    # Move to the beginning of the BytesIO buffer
    image_bytes_io.seek(0)
    # Encode the image data to base64
    return base64.b64encode(image_bytes_io.read()).decode('utf-8')


def convert_pdf_to_images(uploaded_file):
    try:
        # Create a temporary file to store the PDF content
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        # Open the PDF from the temporary file
        pdf_document = fitz.open(tmp_path)
        
        images = []
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            
            # Convert PyMuPDF pixmap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Save the image to an in-memory byte stream
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)  # Move to the beginning of the BytesIO buffer
            
            # Append the byte stream to the list
            images.append(img_byte_arr)
        
        pdf_document.close()
        # Clean up the temporary file
        os.unlink(tmp_path)
        return images

    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return None
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return []

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not found.")
OpenAI.api_key = openai_api_key
client = OpenAI()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    
    
def calculate_duration(date_ranges):
    """
    Calculate total duration from a list of date ranges, considering overlaps and gaps.
    
    Args:
        date_ranges: List of tuples containing date strings in format (start_date, end_date)
                    where dates are in "DD-MM-YYYY" format
    
    Returns:
        tuple: (years, months) representing the total duration
    """
    # Convert date strings to datetime objects and sort by start date
    ranges = [(datetime.strptime(start, "%d-%m-%Y"), 
            datetime.now() if not end else datetime.strptime(end, "%d-%m-%Y")) 
            for start, end in date_ranges if start]
    ranges.sort()

    # Merge overlapping ranges
    merged_ranges = []
    if ranges:
        current_start, current_end = ranges[0]
        
        for start, end in ranges[1:]:
            if start <= current_end:  # Overlapping or contiguous range
                current_end = max(current_end, end)
            else:  # Non-overlapping range
                merged_ranges.append((current_start, current_end))
                current_start, current_end = start, end
        
        merged_ranges.append((current_start, current_end))

    # Calculate total duration
    total_months = 0
    for start, end in merged_ranges:
        # Calculate the difference including partial months
        diff = relativedelta(end, start)
        months = diff.years * 12 + diff.months
        
        # If there are any days, round up to next month
        if diff.days > 0:
            months += 1
            
        total_months += months

    # Convert total months to years and months
    years = total_months // 12
    remaining_months = total_months % 12

    return years, remaining_months
    
    

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
 
def extract_info_with_gpt(raw_text, prompt, images):
    cv_prompt = prompt.replace("{DATETIME}", datetime.now().strftime("%Y-%m-%d")) + "\n\n" + raw_text
    encoded_images = []
    for im in images:
        encoded_images.append(encode_image(im))

    messages_content = [
    {
        "type": "text",
        "text": f"{cv_prompt}",
    }
]

# Add each image to the messages_content
    for img in encoded_images:
        messages_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img}"
                },
            }
        )
    # print(cv_prompt)
    # completion = client.chat.completions.create(
    #               model='gpt-4o',
    #               temperature=0,
    #               response_format={ "type": "json_object" },
    #               messages=[
    #                 {"role": "system", "content": "Extract the relevant information from the CV"},
    #                 {"role": "user", "content": cv_prompt },
    #             ])
    
    # response = completion.choices[0].message.content 
    # print(response) 
    completion = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
         messages=[
        {
            "role": "user",
            "content": messages_content,
        }
    ],
    )

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

If something is in the future, calculate it only until today's date {DATETIME}.

Check the examples above and make sure to calculate it correctly! Do not make mistakes!
User will provide raw text extracted from PDF and images of cv. Use both of them so you can check the better formatting and better data understanding from images. 
"""



def calculate_years_months(date1, date2):

    if date1 == "":
        return 0, 0
    
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
                images = convert_pdf_to_images(uploaded_file)
                raw_text = extract_raw_text_from_pdf(uploaded_file)
                extracted_info = extract_info_with_gpt(raw_text, prompt, images)
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
                    total_work_experience = []
                    for work in parsed_profile.workExperience:
                        working_experience.append(work.period)
                        years, months = calculate_years_months(work.periodStart, work.periodEnd)
                        total_work_experience.append((work.periodStart, work.periodEnd))
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
                    total_education_experience = []
                    for edu in parsed_profile.education:
                        education_experience.append(edu.period)
                        years, months = calculate_years_months(edu.periodStart, edu.periodEnd)
                        total_education_experience.append((edu.periodStart, edu.periodEnd))
                        duration_str = ""
                        if years > 0:
                            duration_str += f"{years} year{'s' if years != 1 else ''}"
                        if months > 0:
                            if duration_str:
                                duration_str += " "
                            duration_str += f"{months} month{'s' if months != 1 else ''}"
                        with st.expander(f"{edu.degree} at {edu.educationalInstitution} ({edu.period} : {duration_str})"):
                            st.markdown(edu.description)
                            
                        
                    total_work_exp_y, total_work_exp_m  = calculate_duration(total_work_experience)
                    total_edu_exp_y, total_edu_exp_m = calculate_duration(total_education_experience)
                    
                    if working_experience:
                        st.markdown(f"**Total Work Experience:** {total_work_exp_y} years, {total_work_exp_m} months")
                    
                    if education_experience:
                        st.markdown(f"**Total Education Duration:** {total_edu_exp_y} years, {total_edu_exp_m} months")

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
                    
                
 
if not st.session_state['logged_in']:
    display_login_form()
else:
    display_main_app()


