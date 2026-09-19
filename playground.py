"""Embed custom text using the project's embedding stack.

Run from the repo root:
    uv run --project backend python playground.py

Reads HARGUS_* settings from backend/.env (or environment variables).
"""
import asyncio
import sys

# Add backend src to path so hargus_api is importable without installing
sys.path.insert(0, "backend/src")


async def test_chunking():
    from langchain_core.documents import Document
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import PyPDFLoader
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n" + "-" * 60 + "\n"],
        chunk_size=1024,
        chunk_overlap=128,
    )

    # loader = TextLoader("example_data/generated/vacancy1/strong_Ryan_Thompson/transcript_1.txt")
    # loader = TextLoader("example_data/generated/vacancy1/strong_Ryan_Thompson/cv.pdf")
    loader = PyPDFLoader("example_data/generated/vacancy1/strong_Ryan_Thompson/cv.pdf")

    docs = loader.load()

    lc_docs: list[Document] = []
    for doc in docs:
        chunks = splitter.split_text(doc.page_content)
        for i, chunk in enumerate(chunks):
            lc_docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "candidate_id": None,
                        "workflow_run_id": None,
                        "source_type": "transcript",
                        "chunk_index": i,
                    },
                )
            )
    
    for doc in lc_docs:
        print(f"Chunk {doc.metadata['chunk_index']}:\n{doc.page_content}\n")


async def main() -> None:
    from hargus_api.ai.llm.factory import get_embeddings

    texts = [
        "skills"
        ]

    embeddings = get_embeddings()

    print(f"Embedding provider: {embeddings.__class__.__name__}")
    print(f"Embedding {len(texts)} text(s)...\n")

    vectors = await embeddings.aembed_documents(texts)

    for text, vec in zip(texts, vectors):
        print(f"Text : {text!r}")
        print(f"Dims : {len(vec)}")
        print(f"Full : {vec}")
        print()


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(test_chunking())
