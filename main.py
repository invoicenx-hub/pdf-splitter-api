from fastapi import FastAPI, UploadFile, File, HTTPException
import re, io, base64
from pypdf import PdfReader, PdfWriter

app = FastAPI()

# 英國 NI 號碼正則表達式
NI_PATTERN = re.compile(r'[A-CEGHJ-PR-TW-Z]{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*[A-D]', re.IGNORECASE)

@app.get("/")
def home():
    return {"status": "PDF Splitter Service is Running"}

@app.post("/split-pdf")
async def split_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        
        results = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            match = NI_PATTERN.search(text)
            
            # 找到 NI 號碼或給予預設檔名
            if match:
                ni_number = match.group(0).replace(" ", "").upper()
                filename = f"{ni_number}.pdf"
            else:
                filename = f"UNKNOWN_page_{i+1}.pdf"
            
            # 拆分單頁 PDF
            writer = PdfWriter()
            writer.add_page(page)
            out_buf = io.BytesIO()
            writer.write(out_buf)
            
            # 轉成 Base64 回傳給 n8n
            results.append({
                "filename": filename,
                "page": i + 1,
                "base64": base64.b64encode(out_buf.getvalue()).decode('utf-8')
            })
            
        return {"status": "success", "total_pages": len(results), "files": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))