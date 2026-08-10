from fastapi import FastAPI, UploadFile, File, HTTPException
import re, io, base64, gc
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
        # 讀取檔案
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        total_pages = len(reader.pages)
        
        results = []
        
        # 逐頁處理，節省記憶體
        for i in range(total_pages):
            page = reader.pages[i]
            text = page.extract_text() or ""
            match = NI_PATTERN.search(text)
            
            if match:
                ni_number = match.group(0).replace(" ", "").upper()
                filename = f"{ni_number}.pdf"
            else:
                filename = f"UNKNOWN_page_{i+1}.pdf"
            
            # 建立單頁 PDF
            writer = PdfWriter()
            writer.add_page(page)
            
            out_buf = io.BytesIO()
            writer.write(out_buf)
            pdf_bytes = out_buf.getvalue()
            
            results.append({
                "filename": filename,
                "page": i + 1,
                "base64": base64.b64encode(pdf_bytes).decode('utf-8')
            })
            
            # 手動清空 buffer 釋放記憶體
            out_buf.close()
            
        # 顯式觸發垃圾回收，避免記憶體爆掉
        del contents
        del reader
        gc.collect()

        return {"status": "success", "total_pages": len(results), "files": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
