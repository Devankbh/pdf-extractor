from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF

app = FastAPI()

GRID_SIZE = 20  # You can tweak this later (10–25 recommended)


@app.get("/")
def root():
    return {"message": "PDF Grid Extraction API is running"}


@app.post("/extract-grid")
async def extract_grid(file: UploadFile = File(...)):
    contents = await file.read()

    # Open PDF
    doc = fitz.open(stream=contents, filetype="pdf")

    response_pages = []

    for page_num, page in enumerate(doc):
        page_width = page.rect.width
        page_height = page.rect.height

        # -----------------------------
        # 1. WORD-LEVEL EXTRACTION
        # -----------------------------
        words_raw = page.get_text("words")

        blocks = []
        for i, w in enumerate(words_raw):
            x0, y0, x1, y1, text, *_ = w

            blocks.append({
                "id": f"p{page_num}_w{i}",
                "text": text,
                "page": page_num + 1,
                "bbox": {
                    "x": x0,
                    "y": y0,
                    "width": x1 - x0,
                    "height": y1 - y0
                }
            })

        # -----------------------------
        # 2. CREATE GRID
        # -----------------------------
        rows = int(page_height // GRID_SIZE)
        cols = int(page_width // GRID_SIZE)

        grid = []
        cell_map = {}

        for r in range(rows):
            for c in range(cols):
                cell_id = f"p{page_num}_cell_{r}_{c}"

                cell = {
                    "id": cell_id,
                    "row": r,
                    "col": c,
                    "page": page_num + 1,
                    "bbox": {
                        "x": c * GRID_SIZE,
                        "y": r * GRID_SIZE,
                        "width": GRID_SIZE,
                        "height": GRID_SIZE
                    },
                    "word_ids": []
                }

                grid.append(cell)
                cell_map[(r, c)] = cell

        # -----------------------------
        # 3. MAP WORDS → GRID CELLS
        # -----------------------------
        for word in blocks:
            x = word["bbox"]["x"]
            y = word["bbox"]["y"]
            w = word["bbox"]["width"]
            h = word["bbox"]["height"]

            start_col = int(x // GRID_SIZE)
            end_col = int((x + w) // GRID_SIZE)

            start_row = int(y // GRID_SIZE)
            end_row = int((y + h) // GRID_SIZE)

            for r in range(start_row, end_row + 1):
                for c in range(start_col, end_col + 1):
                    if (r, c) in cell_map:
                        cell_map[(r, c)]["word_ids"].append(word["id"])

        # -----------------------------
        # 4. PAGE RESPONSE
        # -----------------------------
        response_pages.append({
            "page_meta": {
                "page": page_num + 1,
                "width": page_width,
                "height": page_height,
                "grid_size": GRID_SIZE,
                "rows": rows,
                "cols": cols
            },
            "blocks": blocks,
            "grid": grid
        })

    return {
        "pages": response_pages
    }
