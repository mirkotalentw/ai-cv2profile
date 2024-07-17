from pyresparser import ResumeParser

# Path to the resume file
resume_path = "C:/Users/Talentwunder/Downloads/Mirko_Kalezic_CV_1.pdf"

# Parse the resume
data = ResumeParser(resume_path).get_extracted_data()

# Extracted information
print(data)