import re
# from openai import OpenAI
from langfuse.openai import OpenAI
import os
import streamlit as st
from dotenv import load_dotenv
import json
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional
import fitz  # PyMuPDF
import streamlit as st
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse, urlunparse
import base64
from pdf2image import convert_from_bytes
import io
import tempfile
import os
from PIL import Image
from io import BytesIO
from langfuse import Langfuse


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

LANGFUSE_SECRET_KEY = os.getenv('LANGFUSE_SECRET_KEY')
LANGFUSE_PUBLIC_KEY = os.getenv('LANGFUSE_PUBLIC_KEY')
LANGFUSE_HOST = os.getenv('LANGFUSE_HOST')

langfuse = Langfuse(
  secret_key=LANGFUSE_SECRET_KEY,
  public_key=LANGFUSE_PUBLIC_KEY,
  host=LANGFUSE_HOST
)

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


prompt = """
Please extract the following details from the CV:

1. Biography
2. Work Experience and Education
3. Total work experience duration
4. Total education duration
5. For each position or educational experience:
   - Job Title or Degree
   - Company or Institution
   - Dates (Start and End)
   - Total Length (years and months)
   - Description of responsibilities, achievements, or skills gained
6. Skills
7. Languages
8. Publications
9. Projects

### Output JSON Format
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
            "periodStart": "",  # Format: DD-MM-YYYY
            "periodEnd": "",    # Format: DD-MM-YYYY
            "totalLength": "",  # Total years and months for the position.
            "description": ""
        }
    ],
    "education": [
        {
            "degree": "",
            "educationalInstitution": "",
            "period": "",
            "periodStart": "",  # Format: DD-MM-YYYY
            "periodEnd": "",    # Format: DD-MM-YYYY
            "totalLength": "",  # Total years and months for the degree.
            "description": ""
        }
    ],
    "skills": [],
    "languages": [
        {
            "name": "",
            "degree": ""  # Options: Beginner, Good, Fluent, Proficient, Native/Bilingual
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

### Instructions
1. Use raw text from the uploaded CV to extract the data exactly as it appears. No summaries, no omissions.
2. Use the provided image of the CV to:
   - Verify the classification of sections (e.g., Work Experience vs. Education).
   - Resolve ambiguities in dates, roles, or descriptions.
3. Leave fields empty if information is missing.

### Special Rules
1. **Name, Emails, Phones, Links, and Location**:
   - Extract from biography or contact information sections. Do not infer.
2. **Work Experience**:
   - Extract all positions with full details:
     - Normalize missing months to January.
     - If only one date is provided, verify using the CV image to determine if it's the start or end date. If uncertain, ignore. If there is only end date, do not assume start date, so only extract end date. In that case it is not possible to calculate totalLength. If at least of one of experiences cannot be calculated, DO NOT calculate totalEducationDuration (leave empty). Check CV image to verify if it is a work experience or education and if it start or end date. If there is a dilemma which date it is, do not make assumptions, leave both dates empty.
     - Assume ongoing roles end today: {DATETIME}.
   - Calculate **totalLength** correctly:
     - Do not include the last month if it's incomplete.
     - Example: Feb 2022 - Feb 2023 = 12 months (1 year).
   - Include verbatim descriptions of responsibilities and achievements.
3. **Education**:
   - Follow the same rules for periods and descriptions as Work Experience.
   - For degrees with incomplete dates, check if other education entries also lack dates. If all dates are incomplete, leave periods empty. If there is only end date, do not assume start date, so only extract end date. In that case it is not possible to calculate totalLength. If at least of one of experiences cannot be calculated, DO NOT calculate totalEducationDuration (leave empty).
4. **Skills**:
   - List only the skill names (e.g., "Python", "SQL"). Exclude qualifiers.
5. **Languages**:
   - Normalize proficiency levels to: Beginner, Good, Fluent, Proficient, Native/Bilingual or empty.
6. **Publications and Projects**:
   - Extract all details, including dates, description, and relevant URLs.
   - For Projects, include skills used.

### Examples
1. Correct Work Experience Format:
{
    "jobTitle": "Data Scientist",
    "company": "CompanyA",
    "period": "Jan 2023 - ",
    "periodStart": "01-01-2023",
    "periodEnd": "",
    "totalLength": "1 year 7 months",
    "description": "Working on machine learning and AI projects."
}

2. Correct Education Format:
{
    "degree": "Ph.D. in Computer Science",
    "educationalInstitution": "Stanford University",
    "period": "2019 - ",
    "periodStart": "01-01-2019",
    "periodEnd": "",
    "totalLength": "5 years 11 months",
    "description": ""
}

3. Correct Skills:
["Python", "Machine Learning", "Data Analysis"]

4. Correct Languages:
[
    {"name": "English", "degree": "Native/Bilingual"},
    {"name": "Spanish", "degree": "Proficient"}
]

### Notes
- **Current Date**: {DATETIME}
- Validate all durations for accuracy.
- Ensure periods are normalized to `DD-MM-YYYY` format.
- Check the CV image for context and proper classification of sections.

IMPORTANT NOTE FOR DATES:
1. **General Rules for Dates**:
   - If only one **year** is mentioned (e.g., "2021 VegalIT Full Stack Developer"), leave `periodStart` and `periodEnd` fields **empty**.
   - If both a **month** and **year** are provided, use them for `periodStart` or `periodEnd`.
   - If the date is open-ended (e.g., "2021 - ", "to present", "ongoing", or similar), use the **current date** ({DATETIME}) for `periodEnd`.
   - If dates are written in a format like "Sep 2014 - 2018", **DO NOT normalize or assume a missing end month.** Keep the raw period.

2. **Specific Cases**:
   - If **only years** are mentioned (e.g., "2014 - 2018"), assume the dates are:
     - `periodStart`: "01-01-2014"
     - `periodEnd`: "01-01-2018"
     - Then calculate the `totalLength` based on this assumption.
   - If the period is written as "2019 - ", assume:
     - `periodStart`: "01-01-2019"
     - `periodEnd`: Current Date ({DATETIME}).
   - For periods with **incomplete dates** (e.g., "2021"), leave both `periodStart` and `periodEnd` **empty** and exclude it from total duration calculations (`totalWorkExperience` or `totalEducationDuration`).

3. **Total Length Calculations**:
   - Always calculate `totalLength` for entries with valid `periodStart` and `periodEnd`.
   - If dates are missing or ambiguous (e.g., only a year is provided), do not calculate `totalLength` for that entry.
   - Example:
     - "2017-2020" translates to:
       - `periodStart`: "01-01-2017"
       - `periodEnd`: "01-01-2020"
       - `totalLength`: "3 years".
     - If only "2017" is mentioned:
       - `periodStart`: ""
       - `periodEnd`: ""
       - `totalLength`: ""

4. **Handling Edge Cases**:
   - If multiple entries in Work Experience or Education have only years (e.g., "2018 - ", "2020 - Present"), ensure consistency by normalizing as described above.
   - Use the CV image to resolve ambiguities when deciding whether an entry should be treated as ongoing or closed.

5. **Examples**:
   - Correct Extraction:
     {
         "jobTitle": "IT Support",
         "company": "NCR Voyix",
         "period": "19.06.2023 - ",
         "periodStart": "19-06-2023",
         "periodEnd": "{DATETIME}",
         "totalLength": "1 year 6 months",
         "description": "..."
     }
   - Correct Handling of Only Years:
     {
         "jobTitle": "Private Tutor",
         "company": "Adobe Programs",
         "period": "2017 - 2020",
         "periodStart": "01-01-2017",
         "periodEnd": "01-01-2020",
         "totalLength": "3 years",
         "description": "..."
     }

This applies to all experiences where only the year is provided. DO NOT assume a start or end month unless explicitly mentioned in the CV.
"""

    
    

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
    
    pil_images = []
    total_height = 0
    max_width = 0
    
    for img_bytes in images:
        img = Image.open(img_bytes)
        pil_images.append(img)
        total_height += img.height
        max_width = max(max_width, img.width)
    
    # Create new image with combined height
    combined_image = Image.new('RGB', (max_width, total_height))
    
    # Paste images
    y_offset = 0
    for img in pil_images:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.height
    
    # Convert to bytes
    combined_bytes = BytesIO()
    combined_image.save(combined_bytes, format='PNG')
    encoded_image = encode_image(combined_bytes)

    messages_content = [
        {
            "type": "text",
            "text": f"{cv_prompt}",
        }
    ]
    
    messages_content.append(
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encoded_image}"
            },
        }
    )
        

    completion = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
         messages=[
            {
                "role": "user",
                "content": messages_content,
            }
        ],
        temperature=0,
        top_p=1
    )

    response = completion.choices[0].message.content 
    return response.strip()




def calculate_years_months(date1, date2):

    if date1 == "":
        return 0, 0
    
    d1 = datetime.strptime(date1, "%d-%m-%Y")
    
    if date2 == "":
        d2 = datetime.now()
    else:
        d2 = datetime.strptime(date2, "%d-%m-%Y")
        d2 = d2 - timedelta(days=1)
    
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
                        if (duration_str==""):
                            duration_str=work.totalLength
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
                        if (duration_str==""):
                            duration_str=edu.totalLength
                        with st.expander(f"{edu.degree} at {edu.educationalInstitution} ({edu.period} : {duration_str})"):
                            st.markdown(edu.description)
                            
                        
                    total_work_exp_y, total_work_exp_m  = calculate_duration(total_work_experience)
                    total_edu_exp_y, total_edu_exp_m = calculate_duration(total_education_experience)
                    
                    if working_experience:
                        if ((total_work_exp_y==0) and (total_work_exp_m==0)):
                            st.markdown(f"**Total Work Experience:** {parsed_profile.totalWorkExperience}")
                        else:
                            st.markdown(f"**Total Work Experience:** {total_work_exp_y} years, {total_work_exp_m} months")
                    
                    if education_experience:
                        if ((total_edu_exp_m==0) and (total_edu_exp_y==0)):
                            st.markdown(f"**Total Education Duration:** {parsed_profile.totalEducationDuration}")
                        else:
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


