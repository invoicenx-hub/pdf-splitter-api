from fastapi import FastAPI, UploadFile, File, HTTPException, Form
import re, io, base64, gc
from pypdf import PdfReader, PdfWriter

app = FastAPI()

NI_PATTERN = re.compile(r'[A-CEGHJ-PR-TW-Z]{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*[A-D]', re.IGNORECASE)

# 1. 快速獲取總頁數（極輕量，不佔記憶體）
@app.post("/get-page-count")
async def get_page_count(file: UploadFile = File(...)):
    contents = await file.read()
    reader = PdfReader(io.BytesIO(contents))
    return {"total_pages": len(reader.pages)}

# 2. 分段處理 PDF (例如只處理第 1-50 頁)
@app.post("/split-pdf-range")
async def split_pdf_range(
    file: UploadFile = File(...),
    start_page: int = Form(0),  # 0-indexed
    end_page: int = Form(50)
):
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        total_pages = len(reader.pages)
        
        # 邊界保護
        actual_end = min(end_page, total_pages)
        results = []
        
        for i in range(start_page, actual_end):
            page = reader.pages[i]
            text = page.extract_text() or ""
            match = NI_PATTERN.search(text)
            
            filename = f"{match.group(0).replace(' ', '').upper()}.pdf" if match else f"UNKNOWN_page_{i+1}.pdf"
            
            writer = PdfWriter()
            writer.add_page(page)
            out_buf = io.BytesIO()
            writer.write(out_buf)
            
            results.append({
                "filename": filename,
                "page": i + 1,
                "base64": base64.b64encode(out_buf.getvalue()).decode('utf-8')
            })
            out_buf.close()
            
        del contents
        del reader
        gc.collect()

        return {
            "status": "success",
            "processed_count": len(results),
            "files": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
