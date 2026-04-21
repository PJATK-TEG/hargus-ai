from __future__ import annotations

from hargus_api.schemas.domain import Candidate, Message, Vacancy

_VACANCIES = [
    {
        "id": "v1",
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "San Francisco, CA",
        "type": "full-time",
        "status": "active",
        "description": (
            "We are looking for a Senior Backend Engineer to design, build, and maintain "
            "scalable distributed systems."
        ),
        "requirements": ["5+ years Python/Go", "Distributed systems", "PostgreSQL & Redis"],
        "createdAt": "2026-03-10",
        "candidatesCount": 24,
        "hiresTarget": 2,
    },
    {
        "id": "v2",
        "title": "ML Engineer - NLP",
        "department": "AI/ML",
        "location": "Remote",
        "type": "remote",
        "status": "active",
        "description": "Join our NLP team to build language models and deploy them at scale.",
        "requirements": ["PyTorch/JAX", "Transformer architectures", "Fine-tuning LLMs"],
        "createdAt": "2026-03-05",
        "candidatesCount": 18,
        "hiresTarget": 1,
    },
    {
        "id": "v3",
        "title": "Product Designer",
        "department": "Design",
        "location": "New York, NY",
        "type": "full-time",
        "status": "paused",
        "description": "Craft intuitive enterprise interfaces for a data-heavy recruiting product.",
        "requirements": ["Figma", "Design systems", "User research"],
        "createdAt": "2026-02-20",
        "candidatesCount": 12,
        "hiresTarget": 1,
    },
]

_CANDIDATES = [
    {
        "id": "c1",
        "name": "Elena Kowalski",
        "email": "elena.k@email.com",
        "phone": "+1 (415) 555-0142",
        "location": "San Francisco, CA",
        "avatarInitials": "EK",
        "avatarColor": "#7C3AED",
        "vacancyId": "v1",
        "score": 92,
        "relevancyScore": 88,
        "tags": [
            {"id": "t1", "label": "Strong Fit", "color": "emerald"},
            {"id": "t2", "label": "Ex-FAANG", "color": "purple"},
        ],
        "status": "interview",
        "parsedFields": {
            "summary": (
                "Experienced backend engineer with 8 years building distributed systems "
                "at scale."
            ),
            "skills": ["Python", "Go", "PostgreSQL", "Redis", "Kafka"],
            "skillScores": [
                {"skill": "Python", "score": 95},
                {"skill": "Go", "score": 88},
                {"skill": "System Design", "score": 94},
            ],
            "experience": [
                {
                    "company": "Stripe",
                    "role": "Senior Software Engineer",
                    "from": "2022",
                    "to": "Present",
                    "description": (
                        "Led payment processing pipeline redesign handling high transaction "
                        "volume."
                    ),
                }
            ],
            "education": [
                {
                    "institution": "Stanford University",
                    "degree": "M.S.",
                    "field": "Computer Science",
                    "year": "2017",
                }
            ],
            "languages": ["English", "Polish"],
            "certifications": ["AWS Solutions Architect"],
            "totalYearsExp": 8,
        },
        "files": [
            {
                "id": "f1",
                "type": "cv",
                "name": "Elena_Kowalski_Resume.pdf",
                "content": "Full CV content...",
                "uploadedAt": "2026-03-12",
                "size": "248 KB",
            },
            {
                "id": "f2",
                "type": "transcript",
                "name": "Technical_Interview_Round1.txt",
                "content": "Interviewer: Can you walk us through payment processing design?",
                "uploadedAt": "2026-03-15",
                "size": "12 KB",
            },
        ],
        "appliedAt": "2026-03-12",
        "linkedinUrl": "https://linkedin.com/in/elenakowalski",
    },
    {
        "id": "c2",
        "name": "Marcus Chen",
        "email": "marcus.c@email.com",
        "phone": "+1 (415) 555-0198",
        "location": "Oakland, CA",
        "avatarInitials": "MC",
        "avatarColor": "#06B6D4",
        "vacancyId": "v1",
        "score": 78,
        "relevancyScore": 72,
        "tags": [{"id": "t4", "label": "Good Fit", "color": "cyan"}],
        "status": "screening",
        "parsedFields": {
            "summary": "Full-stack engineer transitioning toward backend work.",
            "skills": ["Python", "Node.js", "PostgreSQL", "Docker"],
            "skillScores": [
                {"skill": "Python", "score": 82},
                {"skill": "Node.js", "score": 75},
                {"skill": "System Design", "score": 55},
            ],
            "experience": [
                {
                    "company": "Notion",
                    "role": "Software Engineer",
                    "from": "2023",
                    "to": "Present",
                    "description": "Worked on collaboration features and internal tooling.",
                }
            ],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "B.S.",
                    "field": "Computer Science",
                    "year": "2021",
                }
            ],
            "languages": ["English", "Mandarin"],
            "certifications": [],
            "totalYearsExp": 5,
        },
        "files": [
            {
                "id": "f5",
                "type": "cv",
                "name": "Marcus_Chen_CV.pdf",
                "content": "Full CV content...",
                "uploadedAt": "2026-03-14",
                "size": "192 KB",
            }
        ],
        "appliedAt": "2026-03-14",
    },
    {
        "id": "c3",
        "name": "Sofia Andersson",
        "email": "sofia.a@email.com",
        "phone": "+46 70 555 0199",
        "location": "Stockholm, Sweden",
        "avatarInitials": "SA",
        "avatarColor": "#10B981",
        "vacancyId": "v2",
        "score": 89,
        "relevancyScore": 94,
        "tags": [{"id": "t11", "label": "NLP Expert", "color": "purple"}],
        "status": "interview",
        "parsedFields": {
            "summary": "NLP researcher turned ML engineer with production and research experience.",
            "skills": ["PyTorch", "Transformers", "Python", "RAG"],
            "skillScores": [
                {"skill": "PyTorch", "score": 96},
                {"skill": "NLP/Transformers", "score": 98},
                {"skill": "RAG Systems", "score": 90},
            ],
            "experience": [
                {
                    "company": "Cohere",
                    "role": "Senior ML Engineer",
                    "from": "2023",
                    "to": "Present",
                    "description": "Leading RAG pipeline development for enterprise search.",
                }
            ],
            "education": [
                {
                    "institution": "KTH Royal Institute",
                    "degree": "Ph.D.",
                    "field": "Machine Learning",
                    "year": "2020",
                }
            ],
            "languages": ["English", "Swedish"],
            "certifications": [],
            "totalYearsExp": 6,
        },
        "files": [
            {
                "id": "f11",
                "type": "cv",
                "name": "Sofia_Andersson_CV.pdf",
                "content": "Full CV content...",
                "uploadedAt": "2026-03-08",
                "size": "285 KB",
            }
        ],
        "appliedAt": "2026-03-08",
        "linkedinUrl": "https://linkedin.com/in/sofiaandersson",
    },
]

_MESSAGES = {
    "c1": [
        {
            "id": "m1",
            "role": "user",
            "content": (
                "What are the key strengths of this candidate for the Senior Backend "
                "Engineer role?"
            ),
            "timestamp": "2026-03-15T10:30:00Z",
        },
        {
            "id": "m2",
            "role": "assistant",
            "content": (
                "Strong backend depth, high system design score, and proven scale at "
                "previous companies."
            ),
            "timestamp": "2026-03-15T10:30:15Z",
        },
    ],
    "c3": [
        {
            "id": "m5",
            "role": "user",
            "content": "How strong is Sofia for the ML Engineer role?",
            "timestamp": "2026-03-20T14:00:00Z",
        },
        {
            "id": "m6",
            "role": "assistant",
            "content": "Very strong fit due to transformer, RAG, and production ML experience.",
            "timestamp": "2026-03-20T14:00:30Z",
        },
    ],
}

VACANCIES = [Vacancy.model_validate(item) for item in _VACANCIES]
CANDIDATES = [Candidate.model_validate(item) for item in _CANDIDATES]
MESSAGES = {
    candidate_id: [Message.model_validate(item) for item in items]
    for candidate_id, items in _MESSAGES.items()
}
