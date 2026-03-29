from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF

app = FastAPI()


# -------------------------
# 🔥 NEW: FIELD EXTRACTION
# -------------------------
def extract_fields(logical_grid):
    fields = []

    for row in logical_grid:
        cells = row["cells"]

        if len(cells) >= 2:
            field_name = " ".join(cells[:-1])
            field_value = cells[-1]

            fields.append({
                "field": field_name.strip(),
                "value": field_value.strip()
            })

        elif len(cells) == 1:
            fields.append({
                "field": cells[0].strip(),
                "value": ""
            })

    return fields


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
        # STEP 2: LOGICAL GRID
        # -------------------------
        blocks_sorted = sorted(
            blocks,
            key=lambda w: (round(w["bbox"]["y"], 1), w["bbox"]["x"])
        )

        rows = []
        threshold = 12

        for word in blocks_sorted:
            y = word["bbox"]["y"]
            placed = False

            for row in rows:
                if abs(row["y"] - y) < threshold:
                    row["words"].append(word)
                    row["y"] = (row["y"] + y) / 2  # stabilize
                    placed = True
                    break

            if not placed:
                rows.append({
                    "y": y,
                    "words": [word]
                })

        logical_grid = []

        for i, row in enumerate(rows):
            sorted_words = sorted(row["words"], key=lambda w: w["bbox"]["x"])

            logical_grid.append({
                "row_id": i,
                "cells": [w["text"] for w in sorted_words],
                "text": " ".join([w["text"] for w in sorted_words])
            })

        # -------------------------
        # 🔥 STEP 3: FIELD EXTRACTION
        # -------------------------
        fields = extract_fields(logical_grid)

        # -------------------------
        # STEP 4: PIXEL GRID (UI)
        # -------------------------
        pixel_grid = []

        for i, word in enumerate(blocks):
            pixel_grid.append({
                "id": f"cell_{i}",
                "text": word["text"],
                "bbox": word["bbox"]
            })

        # -------------------------
        # FINAL RESPONSE
        # -------------------------
        response_pages.append({
            "page": page_num + 1,
            "blocks": blocks,
            "logical_grid": logical_grid,
            "fields": fields,  # 🔥 NEW OUTPUT
            "pixel_grid": pixel_grid
        })

    return {
        "pages": response_pages
    }
