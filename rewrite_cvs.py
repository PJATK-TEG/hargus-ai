import os
import glob
from langchain_community.document_loaders import PyPDFLoader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

files = glob.glob('example_data/CVs/**/*.pdf', recursive=True)

for file in files:
    print(f"Processing {file}...")
    
    try:
        # Load the text from the original PDF
        loader = PyPDFLoader(file)
        pages = loader.load()
        cv_text = "\n".join([p.page_content for p in pages])
        
        # Clean up text (remove empty lines or weird artifacts)
        lines = [line.strip() for line in cv_text.split('\n') if line.strip()]
        
        # Write to a clean PDF
        doc = SimpleDocTemplate(file, pagesize=letter)
        styles = getSampleStyleSheet()
        styleNormal = styles['Normal']
        
        story = []
        for line in lines:
            story.append(Paragraph(line, styleNormal))
            story.append(Spacer(1, 5))
            
        doc.build(story)
        print(f"Successfully rewrote {file}")
    except Exception as e:
        print(f"Failed to rewrite {file}: {e}")

print("Done rewriting CVs.")
