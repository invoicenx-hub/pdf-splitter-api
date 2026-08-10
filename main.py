from fastapi import FastAPI, UploadFile, File, HTTPException, Form
import re, io, base64, gc
from pypdf import PdfReader, PdfWriter

app = FastAPI()

# 精確匹配 NI/ni 開頭 + 0~多個空格/橫線 + 9 位數字 (例如：NI260800475 或 NI 260800475)
NI_PATTERN = re.compile(r'\bNI[\s-]*\d{9}\b', re.IGNORECASE)

@app.get("/")
def home():
    return {"status": "PDF Splitter Service (NI + 9 Digits Pattern) is Running"}

# 1. 快速獲取總頁數 API
@app.post("/get-page-count")
async def get_page_count(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        total_pages = len(reader.pages)
        
        # 釋放記憶體
        del contents
        del reader
        gc.collect()
        
        return {"total_pages": total_pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. 分頁批次處理 API
@app.post("/split-pdf-range")
async def split_pdf_range(
    file: UploadFile = File(...),
    start_page: int = Form(0),  # 起始頁 (從 0 開始算)
    end_page: int = Form(50)    # 結束頁
):
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        total_pages = len(reader.pages)
        
        # 防止範圍超出總頁數
        actual_end = min(end_page, total_pages)
        results = []
        
        for i in range(start_page, actual_end):
            page = reader.pages[i]
            text = page.extract_text() or ""
            
            # 搜尋 NI260800475 格式
            match = NI_PATTERN.search(text)
            
            if match:
                # 清除可能存在的空格或橫線，並一律轉大寫
                ni_number = re.sub(r'[\s-]', '', match.group(0)).upper()
                filename = f"{ni_number}.pdf"
            else:
                filename = f"UNKNOWN_page_{i+1}.pdf"
            
            # 拆分單頁 PDF
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
            out_buf.close()
            
        # 顯式觸發垃圾回收，保護 Render 免費版 512MB RAM
        del contents
        del reader
        gc.collect()

        return {
            "status": "success",
            "start_page": start_page,
            "end_page": actual_end,
            "files": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
