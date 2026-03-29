from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF

app = FastAPI()

GRID_SIZE = 20  # pixel grid size (UI layer)


# -----------------------------
# 🟢 LOGICAL GRID (ROWS)
# -----------------------------
def build_grid_from_words(words, y_threshold=10):
    words_sorted = sorted(words, key=lambda w: w["bbox"]["y"])
    rows = []

    for word in words_sorted:
        y = word["bbox"]["y"]
        placed = False

        for row in rows:
            if abs(row["y"] - y) < y_threshold:
                row["words"].append(word)
                placed = True
                break

        if not placed:
            rows.append({
                "y": y,
                "words": [word]
            })

    grid = []

    for row in rows:
        sorted_words = sorted(row["words"], key=lambda w: w["bbox"]["x"])

        grid.append([
            {
                "text": w["text"],
                "word_id": w["id"],
                "x": w["bbox"]["x"],
                "y": w["bbox"]["y"]
            }
            for w in sorted_words
        ])

    return grid


# -----------------------------
# 🟡 PIXEL GRID (UI LAYER)
# -----------------------------
def build_pixel_grid(page_width, page_height):
    rows = int(page_height // GRID_SIZE)
    cols = int(page_width // GRID_SIZE)

    grid = []
    cell_map = {}

    for r in range(rows):
        for c in range(cols):
            cell_id = f"cell_{r}_{c}"

            cell = {
                "id": cell_id,
                "row": r,
                "col": c,
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

    return grid, cell_map, rows, cols


# -----------------------------
# 🔵 MAP WORDS → PIXEL GRID
# -----------------------------
def map_words_to_grid(words, cell_map):
    for word in words:
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
# 🟢 ROOT
# -----------------------------
@app.get("/")
def root():
    return {"message": "PDF Grid Extraction API is running"}


# -----------------------------
# 🚀 MAIN API
# -----------------------------
@app.post("/extract-grid")
async def extract_grid(file: UploadFile = File(...)):
    contents = await file.read()
    doc = fitz.open(stream=contents, filetype="pdf")

    response_pages = []

    for page_num, page in enumerate(doc):
        page_width = page.rect.width
        page_height = page.rect.height

        # -----------------------------
        # 1. WORD EXTRACTION
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
        # 2. LOGICAL GRID (ROWS)
        # -----------------------------
        logical_grid = build_grid_from_words(blocks)

        # -----------------------------
        # 3. PIXEL GRID (UI)
        # -----------------------------
        pixel_grid, cell_map, rows, cols = build_pixel_grid(page_width, page_height)

        # -----------------------------
        # 4. MAP WORDS TO GRID
        # -----------------------------
        map_words_to_grid(blocks, cell_map)

        # -----------------------------
        # 5. FINAL RESPONSE
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
            "logical_grid": logical_grid,   # for structure
            "pixel_grid": pixel_grid        # for UI overlay
        })

    return {
        "pages": response_pages
    }
