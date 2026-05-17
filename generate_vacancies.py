import os
import glob
import random
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

llm = Ollama(model="llama3.2:3b") 

prompt = PromptTemplate.from_template("""
You are an expert technical recruiter and hiring manager.
Based on the following candidate's CV text, create a realistic and detailed Job Vacancy (Job Description) 
for a position that this candidate would be a perfect fit for.
Include Job Title, About the Role, Responsibilities, and Requirements.

CV Text:
{cv_text}

Job Vacancy:
""")

output_dir = "example_data/vacancies"
os.makedirs(output_dir, exist_ok=True)

files = glob.glob('example_data/CVs/**/*.pdf', recursive=True)
# Ensure we pick 5 random CVs
random.seed(42) # For reproducibility
random.shuffle(files)
selected_files = files[:5]

for file in selected_files:
    try:
        filename = os.path.basename(file)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}_vacancy.txt")
        
        print(f"Processing {filename}...")
        loader = PyPDFLoader(file)
        pages = loader.load_and_split()
        cv_text = "\n".join([p.page_content for p in pages])
        
        vacancy = llm.invoke(prompt.format(cv_text=cv_text))
        
        with open(output_path, "w") as f:
            f.write(vacancy)
            
        print(f"Saved vacancy to {output_path}")
    except Exception as e:
        print(f"Error processing {file}: {e}")

print("Done generating vacancies!")
