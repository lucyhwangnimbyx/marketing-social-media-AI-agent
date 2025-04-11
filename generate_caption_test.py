from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for the request
class CaptionPrompt(BaseModel):
    prompt: str

# Only /generate-captions endpoint for testing
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