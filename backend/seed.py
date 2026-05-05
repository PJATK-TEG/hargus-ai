import os
import glob
import random
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pypdf import PdfReader
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.models import Vacancy, Candidate, CandidateFile, Message, DocumentChunk

AVATAR_COLORS = ["#7C3AED", "#10B981", "#F59E0B", "#EC4899", "#3B82F6", "#06B6D4", "#F43F5E"]

llm = Ollama(model="llama3.1:8b")

def _clean_json(res: str) -> str:
    res = res.strip()
    if res.startswith("```json"): res = res[7:]
    if res.startswith("```"): res = res[3:]
    if res.endswith("```"): res = res[:-3]
    return res.strip()

def _chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    words = text.split()
    chunks = []
    current_chunk = []
    current_len = 0
    for word in words:
        if current_len + len(word) > chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_len = len(word)
        else:
            current_chunk.append(word)
            current_len += len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

cv_prompt = PromptTemplate.from_template("""
You are an expert HR parser. 
Extract the following information from the given CV text and output ONLY valid JSON.
Do not add any markdown formatting, do not wrap in ```json, just the raw JSON object.

The JSON object must have this exact structure:
{{
  "summary": "A short 1-2 sentence professional summary.",
  "skills": ["Skill 1", "Skill 2"],
  "skillScores": [{{"skill": "Skill 1", "score": 90}}],
  "experience": [{{"company": "string", "role": "string", "from": "string", "to": "string", "description": "string"}}],
  "education": [{{"institution": "string", "degree": "string", "field": "string", "year": "string"}}],
  "languages": ["Language 1"],
  "certifications": ["Cert 1"],
  "totalYearsExp": 5
}}

CV Text:
{cv_text}
""")

vacancy_prompt = PromptTemplate.from_template("""
You are an expert recruiter. Extract the following information from the given job vacancy text and output ONLY valid JSON.
Do not add any markdown formatting, do not wrap in ```json, just the raw JSON object.

The JSON object must have this exact structure:
{{
  "title": "string",
  "department": "string",
  "location": "string",
  "type": "full-time" | "part-time" | "contract" | "remote",
  "description": "string",
  "requirements": ["string"],
  "hiresTarget": integer
}}

Text:
{text}
""")

transcript_prompt = PromptTemplate.from_template("""
You are an expert interviewer. Evaluate this candidate based on their interview transcript.
Output ONLY valid JSON. No markdown formatting, no ```json.

The JSON object must have this exact structure:
{{
  "score": 85,
  "relevancyScore": 88,
  "tags": [{{"id": "t1", "label": "Strong", "color": "emerald"}}]
}}
Colors can be: purple, cyan, emerald, amber, pink, red, indigo.

Transcript:
{text}
""")

def _get_text_from_pdf(filepath: str) -> str:
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
        return text.strip()
    except:
        return ""

def parse_cv_with_ollama(cv_text: str) -> dict:
    try:
        res = llm.invoke(cv_prompt.format(cv_text=cv_text))
        return json.loads(_clean_json(res))
    except Exception as e:
        print(f"Error parsing CV: {e}")
        return {
            "summary": "Error parsing", "skills": [], "skillScores": [],
            "experience": [], "education": [], "languages": [], "certifications": [], "totalYearsExp": 0
        }

def parse_vacancy_with_ollama(text: str, vid: int) -> dict:
    try:
        res = llm.invoke(vacancy_prompt.format(text=text))
        parsed = json.loads(_clean_json(res))
        return {
            "id": f"v{vid}",
            "title": parsed.get("title", f"Vacancy {vid}"),
            "department": parsed.get("department", "Engineering"),
            "location": parsed.get("location", "Remote"),
            "type": parsed.get("type", "full-time"),
            "status": "active",
            "description": parsed.get("description", text[:1000]),
            "requirements": parsed.get("requirements", []),
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "candidatesCount": 0,
            "hiresTarget": parsed.get("hiresTarget", 1)
        }
    except Exception as e:
        print(f"Error parsing Vacancy: {e}")
        return {
            "id": f"v{vid}", "title": f"Vacancy {vid}", "department": "Engineering", "location": "Remote", "type": "full-time", "status": "active", "description": text[:1000], "requirements": [], "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "candidatesCount": 0, "hiresTarget": 1
        }

def evaluate_transcript_with_ollama(text: str) -> dict:
    try:
        res = llm.invoke(transcript_prompt.format(text=text))
        return json.loads(_clean_json(res))
    except Exception as e:
        print(f"Error parsing Transcript: {e}")
        return {"score": random.randint(60, 99), "relevancyScore": random.randint(60, 99), "tags": [{"id": "t1", "label": "Technical", "color": "emerald"}]}

async def seed():
    async with AsyncSessionLocal() as session:
        vac_files = glob.glob('../example_data/vacancies/*.txt')
        if not vac_files: vac_files = glob.glob('example_data/vacancies/*.txt')
             
        vacancies = []
        for i, val in enumerate(vac_files):
            print(f"Parsing Vacancy {i+1}/{len(vac_files)} with Ollama...")
            with open(val, "r") as f:
                vac_text = f.read()
            vac_data = parse_vacancy_with_ollama(vac_text, i+1)
            vacancies.append(vac_data)
            
            vacancy = Vacancy(
                id=vac_data["id"],
                title=vac_data["title"],
                department=vac_data["department"],
                location=vac_data["location"],
                type=vac_data["type"],
                status=vac_data["status"],
                description=vac_data["description"][:1000],
                requirements=vac_data["requirements"],
                created_at=vac_data["createdAt"],
                candidates_count=vac_data["candidatesCount"],
                hires_target=vac_data["hiresTarget"],
            )
            session.add(vacancy)
            
        print(f"Loaded {len(vacancies)} vacancies")

        cv_files = glob.glob('../example_data/CVs/**/*.pdf', recursive=True)
        if not cv_files: cv_files = glob.glob('example_data/CVs/**/*.pdf', recursive=True)

        for i, cv_path in enumerate(cv_files):
            name_ext = os.path.basename(cv_path)
            name_only = os.path.splitext(name_ext)[0]
            readable_name = name_only.replace('_', ' ')
            
            print(f"Parsing CV {i+1}/{len(cv_files)}: {readable_name} with Ollama...")
            cv_text = _get_text_from_pdf(cv_path)
            parsed_fields = parse_cv_with_ollama(cv_text)
            
            transcript_folder = '../example_data/interview_transcripts'
            if not os.path.exists(transcript_folder):
                transcript_folder = 'example_data/interview_transcripts'
                
            transcript_path = os.path.join(transcript_folder, f"{name_only}_transcript.txt")
            transcript_text = ""
            transcript_eval = {"score": random.randint(60, 99), "relevancyScore": random.randint(60, 99), "tags": [{"id": "t1", "label": "Technical", "color": "emerald"}]}
            
            if os.path.exists(transcript_path):
                print(f"Parsing Transcript for {readable_name} with Ollama...")
                with open(transcript_path, 'r') as f:
                    transcript_text = f.read()
                transcript_eval = evaluate_transcript_with_ollama(transcript_text)
            
            first_name = readable_name.split()[0]
            last_name = readable_name.split()[-1] if len(readable_name.split()) > 1 else ""
            email = f"{first_name.lower()}.{last_name.lower()}@email.com"
            initials = f"{first_name[0]}{last_name[0]}" if last_name else f"{first_name[:2]}"
            
            assigned_vac = random.choice(vacancies)
            candidate_id = f"c{i+1}"
            
            candidate = Candidate(
                id=candidate_id,
                name=readable_name,
                email=email,
                phone=f"+1 (555) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
                location="Remote",
                avatar_initials=initials.upper(),
                avatar_color=random.choice(AVATAR_COLORS),
                vacancy_id=assigned_vac["id"],
                score=transcript_eval.get("score", 70),
                relevancy_score=transcript_eval.get("relevancyScore", 70),
                tags=transcript_eval.get("tags", []),
                status="interview",
                parsed_fields=parsed_fields,
                applied_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                linkedin_url=f"https://linkedin.com/in/{first_name.lower()}{last_name.lower()}"
            )
            session.add(candidate)
            
            cv_file = CandidateFile(
                id=f"f{i}_cv",
                candidate_id=candidate_id,
                type="cv",
                name=name_ext,
                content=cv_text,
                uploaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                size=f"{os.path.getsize(cv_path) // 1024} KB"
            )
            session.add(cv_file)

            # Insert document chunks for CV
            workflow_run_id = f"seed_wr_cv_{candidate_id}"
            cv_chunks = _chunk_text(cv_text)
            for idx, chunk_content in enumerate(cv_chunks):
                doc_chunk = DocumentChunk(
                    candidate_id=candidate_id,
                    workflow_run_id=workflow_run_id,
                    source_type="cv",
                    chunk_index=idx,
                    content=chunk_content,
                    chunk_metadata={"source": "CV", "filename": name_ext}
                )
                session.add(doc_chunk)
            
            if transcript_text:
                t_file = CandidateFile(
                    id=f"f{i}_transcript",
                    candidate_id=candidate_id,
                    type="transcript",
                    name=f"{name_only}_transcript.txt",
                    content=transcript_text,
                    uploaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    size=f"{len(transcript_text) // 1024} KB"
                )
                session.add(t_file)

                # Insert document chunks for Transcript
                tr_chunks = _chunk_text(transcript_text)
                for idx, chunk_content in enumerate(tr_chunks):
                    doc_chunk = DocumentChunk(
                        candidate_id=candidate_id,
                        workflow_run_id=workflow_run_id,
                        source_type="transcript",
                        chunk_index=idx,
                        content=chunk_content,
                        chunk_metadata={"source": "Transcript", "filename": f"{name_only}_transcript.txt"}
                    )
                    session.add(doc_chunk)

        await session.commit()
        print(f"Database seeded successfully with {len(cv_files)} candidates and document chunks!")

if __name__ == "__main__":
    asyncio.run(seed())
