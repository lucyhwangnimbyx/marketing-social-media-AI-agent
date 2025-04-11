from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Literal, List
from pathlib import Path
import os
from dotenv import load_dotenv

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader, Docx2txtLoader

# Load environment variables
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")

if not openai_key:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")

# Initialize FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Paths
UPLOAD_DIR = Path("uploaded_docs")
UPLOAD_DIR.mkdir(exist_ok=True)
IMAGE_DIR = Path("uploaded_images")
IMAGE_DIR.mkdir(exist_ok=True)

# Vectorstore init
embedding = OpenAIEmbeddings(openai_api_key=openai_key)
if Path("marketing_index").exists():
    vectorstore = FAISS.load_local("marketing_index", embedding, allow_dangerous_deserialization=True)
    print("✅ Loaded existing FAISS index.")
else:
    vectorstore = FAISS.from_texts(["Welcome to marketing RAG!"], embedding)
    vectorstore.save_local("marketing_index")
    print("✅ Created and saved new FAISS index.")

# Text loader helper
def load_documents(file_path: str, file_ext: str):
    if file_ext == ".pdf":
        loader = PyMuPDFLoader(file_path)
    elif file_ext == ".docx":
        loader = Docx2txtLoader(file_path)
    elif file_ext in [".txt", ".md"]:
        loader = TextLoader(file_path)
    else:
        raise ValueError("Unsupported file type")
    return loader.load()

# Upload text endpoint
@app.post("/upload-text")
async def upload_text(file: UploadFile = File(...)):
    file_ext = Path(file.filename).suffix.lower()
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        f.write(await file.read())
    try:
        documents = load_documents(str(save_path), file_ext)
        vectorstore.add_documents(documents)
        vectorstore.save_local("marketing_index")
        return {
            "message": f"{file.filename} uploaded and indexed successfully",
            "content_preview": documents[0].page_content[:200] if documents else "No content"
        }
    except ValueError as e:
        return {"error": str(e)}

# Upload media (images/videos)
@app.post("/upload-media")
async def upload_media(files: List[UploadFile] = File(...)):
    results = []
    for file in files[:10]:
        path = IMAGE_DIR / file.filename
        with open(path, "wb") as f:
            f.write(await file.read())
        results.append({"filename": file.filename, "status": "uploaded"})
    return {"results": results}

# Caption generation
class CaptionPrompt(BaseModel):
    prompt: str

@app.post("/generate-captions")
async def generate_captions(data: CaptionPrompt):
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_key)
    query = f"""
    Based on the following description, generate:
    1. A creative post title
    2. A short caption
    3. A list of 5-8 relevant hashtags

    Description: {data.prompt}
    """
    result = llm.invoke(query)
    return {"generated": result}
