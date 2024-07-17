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
 
# Define the prompt for extracting relevant information
# prompt = """
# Extract the following details from the CV:
# - Biography
# - Work Experience and Education in the following format (do not use this in rsponse, this is just formating example):
#     6 years work experience in total
#     8 years education in total
#     Freelance Frontend Developer
#     DivvyDiary
#     Nov 2020 - Jan 2021 ( 3 months)
#     I implemented a multi-language mode on this website. This made it possible for the site to get clients from English speaking countries.
#     SPICED Academy
#     Jan 2020 - Dec 2020 ( 1 year )
#     During the course, we solidified the fundamentals of JavaScript(ES5 and ES6), HTML and CSS. We independently developed applications within deadlines, using Node, SQL, Redis, Express, Vue and React while embracing a culture of sharing information and inspiration.
#     Full Stack Web Developer Certificate
#     Professional Bass Player
#     Musician, Bassist, Self Employed
#     Jul 2015 - Mar 2020 ( 4 years 9 months)
#     During my professional music career, I learned what it means to work in a small team. We created show concepts and mastered a lot of difficult situations (every concert venue or festival is different). I learned what it means to be reliable when playing for artists like Max Giesinger, Lotte, and more.
#     Popacademy, Major in Bass Guitar
#     ArtEZ hogeschool voor de kunsten
#     Jan 2011 - Dec 2015 ( 5 years )
#     Music has always been a passion, so I studied my main instrument, the bass guitar. During the conservatory years, I learned what it takes to truly master a skill, to get up and practice even if you don’t feel like it, to work on small details for hours, but also to savor every bit of progress that I made.
#     Bachelor of Music)
# - Skills
# - Languages
# """
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
Format Example:

Biography

Work Experience:

6 years work experience in total
Freelance Frontend Developer at DivvyDiary (Nov 2020 - Jan 2021, 3 months)
Implemented a multi-language mode on the website, increasing client base from English-speaking countries.
Professional Bass Player at Self Employed (Jul 2015 - Mar 2020, 4 years 9 months)
Worked in small teams to create show concepts and handled various performance situations. Played for artists like Max Giesinger and Lotte.
Education:

8 years education in total
Full Stack Web Developer Certificate from SPICED Academy (Jan 2020 - Dec 2020, 1 year)
Solidified fundamentals of JavaScript (ES5 and ES6), HTML, and CSS. Developed applications using Node, SQL, Redis, Express, Vue, and React.
Bachelor of Music in Bass Guitar from ArtEZ hogeschool voor de kunsten (Jan 2011 - Dec 2015, 5 years)
Studied bass guitar, mastering the skill through dedicated practice and attention to detail.
Skills:

List of skills
Languages:

List of languages
Please ensure the extracted details are organized and formatted as shown in the example.
Also, please do not extract the other things that are not mentioned in the prompt (e.g. licenses, certifications, etc.).
"""
 
# Path to your CV PDF
pdf_path = "C:/Users/Talentwunder/Desktop/AI/ai-internal-cv2profile/resumes/cvjovanasekaric.pdf"
 
# Extract raw text from PDF
raw_text = extract_raw_text_from_pdf(pdf_path)
 
# Get the extracted information
extracted_info = extract_info_with_gpt(raw_text, prompt)
print(extracted_info)