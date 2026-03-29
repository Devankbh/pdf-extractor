from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF

app = FastAPI()

GRID_SIZE = 20


# -------------------------
# GRID BUILD
# -------------------------
def build_full_grid(page_width, page_height):
    rows = int(page_height // GRID_SIZE) + 1
    cols = int(page_width // GRID_SIZE) + 1

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
                "word_ids": [],
                "text": ""  # 🔥 added
            })

    return grid, rows, cols


# -------------------------
# MAP WORDS → GRID CELLS
# -------------------------
def map_words_to_grid(blocks, grid, rows, cols):

    for word in blocks:
        x = word["bbox"]["x"]
        y = word["bbox"]["y"]
        w = word["bbox"]["width"]
        h = word["bbox"]["height"]

        start_col = int(x // GRID_SIZE)
        end_col = int((x + w) // GRID_SIZE)

        start_row = int(y // GRID_SIZE)
        end_row = int((y + h) // GRID_SIZE)

        start_col = max(0, min(start_col, cols - 1))
        end_col = max(0, min(end_col, cols - 1))

        start_row = max(0, min(start_row, rows - 1))
        end_row = max(0, min(end_row, rows - 1))

        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                index = r * cols + c
                grid[index]["word_ids"].append(word["id"])

    filled_cells = [c for c in grid if c["word_ids"]]
    print(f"✅ Cells with words: {len(filled_cells)}")


# -------------------------
# 🔥 ADD TEXT INTO GRID CELLS (FINAL STEP)
# -------------------------
def enrich_grid_with_text(grid, blocks):
    block_map = {b["id"]: b["text"] for b in blocks}

    for cell in grid:
        texts = [block_map.get(wid, "") for wid in cell["word_ids"]]
        cell["text"] = " ".join(texts).strip()


@app.post("/extract-grid")
async def extract_grid(file: UploadFile = File(...)):
    contents = await file.read()
    doc = fitz.open(stream=contents, filetype="pdf")

    response_pages = []

    for page_num, page in enumerate(doc):

        words_raw = page.get_text("words")
        print(f"📄 Page {page_num+1} → words extracted: {len(words_raw)}")

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

        page_width = page.rect.width
        page_height = page.rect.height

        grid, rows, cols = build_full_grid(page_width, page_height)

        # 🔥 mapping
        map_words_to_grid(blocks, grid, rows, cols)

        # 🔥 FINAL STEP (text in cells)
        enrich_grid_with_text(grid, blocks)

        filled_cells = [c for c in grid if c["word_ids"]]
        print(f"✅ Page {page_num+1} → cells with words: {len(filled_cells)}")

        if len(words_raw) > 0 and len(filled_cells) == 0:
            print("🚨 WARNING: mapping failed")

        response_pages.append({
            "page": page_num + 1,
            "page_meta": {
                "width": page_width,
                "height": page_height,
                "grid_size": GRID_SIZE,
                "rows": rows,
                "cols": cols
            },
            "blocks": blocks,
            "grid": grid
        })

    return {"pages": response_pages}
