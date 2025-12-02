# backend/app/core/rag/curriculum_loader.py
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_curriculum():
    curriculum_dir = Path("./curriculum/")
    texts = []
    metadatas = []

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for file in curriculum_dir.rglob("*.txt"):
        content = file.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "source": "curriculum",
                "file": str(file),
                "chunk": i
            })
    return texts, metadatas