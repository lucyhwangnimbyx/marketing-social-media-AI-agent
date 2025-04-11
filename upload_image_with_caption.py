from fastapi import UploadFile, File
from pathlib import Path
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

# 사전 학습된 이미지 caption 모델 불러오기
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

IMAGE_DIR = Path("uploaded_images")
IMAGE_DIR.mkdir(exist_ok=True)

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    save_path = IMAGE_DIR / file.filename
    with open(save_path, "wb") as f:
        f.write(await file.read())

    # 이미지 설명 생성
    raw_image = Image.open(save_path).convert('RGB')
    inputs = processor(raw_image, return_tensors="pt")
    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)

    # 설명을 문서화하여 벡터 DB에 저장
    document = Document(page_content=caption, metadata={"source": file.filename})
    vectorstore = FAISS.load_local("marketing_index", OpenAIEmbeddings())
    vectorstore.add_documents([document])
    vectorstore.save_local("marketing_index")

    return {
        "message": f"{file.filename} uploaded and indexed with caption.",
        "caption": caption
    }