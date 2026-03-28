from fastapi import FastAPI, File, UploadFile
import fitz  # PyMuPDF

app = FastAPI()

@app.post("/extract-blocks")
async def extract_blocks(file: UploadFile = File(...)):
    contents = await file.read()

    with open("temp.pdf", "wb") as f:
        f.write(contents)

    doc = fitz.open("temp.pdf")

    blocks_output = []

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")

        for idx, b in enumerate(blocks):
            x0, y0, x1, y1, text, *_ = b

            text = text.strip()
            if not text:
                continue

            blocks_output.append({
                "block_id": f"{page_num}_{idx}",
                "text": text,
                "page": page_num,
                "bbox": {
                    "x": x0,
                    "y": y0,
                    "width": x1 - x0,
                    "height": y1 - y0
                }
            })

    return {"blocks": blocks_output}