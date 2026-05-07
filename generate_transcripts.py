import os
import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

# Setup Ollama running locally (as indicated by your terminal)
llm = Ollama(model="llama3.1:8b") # using llama3 or adjust to local model

prompt = PromptTemplate.from_template("""
You are a hiring manager interviewing a candidate based on their CV.
Please generate a realistic interview transcript based on the following extracted CV text.
The transcript should be a dialogue between 'Interviewer' and 'Candidate'.
Focus on their past experience, technical skills, and a behavioral question.

CV Text:
{cv_text}

Interview Transcript:
""")

output_dir = "example_data/interview_transcripts"
os.makedirs(output_dir, exist_ok=True)

files = glob.glob('example_data/CVs/**/*.pdf', recursive=True)

for file in files:
    try:
        filename = os.path.basename(file)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}_transcript.txt")
        
        if os.path.exists(output_path):
            print(f"Skipping {filename}, transcript already exists.")
            continue
            
        print(f"Processing {filename}...")
        loader = PyPDFLoader(file)
        pages = loader.load_and_split()
        cv_text = "\n".join([p.page_content for p in pages])
        
        transcript = llm.invoke(prompt.format(cv_text=cv_text))
        
        with open(output_path, "w") as f:
            f.write(transcript)
            
        print(f"Saved transcript to {output_path}")
    except Exception as e:
        print(f"Error processing {file}: {e}")

print("Done generating transcripts!")
