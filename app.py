from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF

app = FastAPI()

# -------------------------
# 🔥 GRID SIZE (core control)
# -------------------------
GRID_SIZE = 20


# -------------------------
# 🟦 BUILD FULL GRID
# -------------------------
def build_full_grid(page_width, page_height):
    rows = int(page_height // GRID_SIZE)
    cols = int(page_width // GRID_SIZE)

    grid = []

    for r in range(rows):
        for c in range(cols):
            grid.append({
                "row": r,
                "col": c,
                "bbox": {
                    "x": c * GRID_SIZE,
                    "y": r * GRID_SIZE,
                    "width": GRID_SIZE,
                    "height": GRID_SIZE
                },
                "word_ids": []
            })

    return grid, rows, cols


# -------------------------
# 🟨 MAP WORDS → GRID CELLS (FINAL FIX)
# -------------------------
def map_words_to_grid(blocks, grid):
    for word in blocks:
        x = word["bbox"]["x"]
        y = word["bbox"]["y"]
        w = word["bbox"]["width"]
        h = word["bbox"]["height"]

        # ✅ Use CENTER POINT (reliable mapping)
        center_x = x + w / 2
        center_y = y + h / 2

        for cell in grid:
            cx = cell["bbox"]["x"]
            cy = cell["bbox"]["y"]
            cw = cell["bbox"]["width"]
            ch = cell["bbox"]["height"]

            if (
                cx <= center_x <= cx + cw and
                cy <= center_y <= cy + ch
            ):
                cell["word_ids"].append(word["id"])
                break  # ✅ prevent duplicate mapping


@app.post("/extract-grid")
async def extract_grid(file: UploadFile = File(...)):
    contents = await file.read()
    doc = fitz.open(stream=contents, filetype="pdf")

    response_pages = []

    for page_num, page in enumerate(doc):

        # -------------------------
        # STEP 1: WORD EXTRACTION
        # -------------------------
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

        # -------------------------
        # STEP 2: BUILD GRID
        # -------------------------
        page_width = page.rect.width
        page_height = page.rect.height

        grid, total_rows, total_cols = build_full_grid(page_width, page_height)

        # -------------------------
        # STEP 3: MAP WORDS TO GRID
        # -------------------------
        map_words_to_grid(blocks, grid)

        # -------------------------
        # 🔍 DEBUG CHECK (optional)
        # -------------------------
        filled_cells = [c for c in grid if len(c["word_ids"]) > 0]
        print(f"Page {page_num+1} → cells with words: {len(filled_cells)}")

        # -------------------------
        # FINAL RESPONSE
        # -------------------------
        response_pages.append({
            "page": page_num + 1,
            "page_meta": {
                "width": page_width,
                "height": page_height,
                "grid_size": GRID_SIZE,
                "rows": total_rows,
                "cols": total_cols
            },
            "blocks": blocks,
            "grid": grid
        })

    return {
        "pages": response_pages
    }
