from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF

app = FastAPI()


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
        # STEP 2: LOGICAL GRID (ROWS)
        # -------------------------
        rows = []

        for word in blocks:
            y = word["bbox"]["y"]

            placed = False

            for row in rows:
                if abs(row["y"] - y) < 10:
                    row["words"].append(word)
                    placed = True
                    break

            if not placed:
                rows.append({
                    "y": y,
                    "words": [word]
                })

        logical_grid = []

        for i, row in enumerate(sorted(rows, key=lambda r: r["y"])):

            sorted_words = sorted(row["words"], key=lambda w: w["bbox"]["x"])

            logical_grid.append({
                "row_id": i,
                "cells": [w["text"] for w in sorted_words]
            })

        # -------------------------
        # STEP 3: PIXEL GRID (UI)
        # -------------------------
        pixel_grid = []

        for i, word in enumerate(blocks):
            pixel_grid.append({
                "id": f"cell_{i}",
                "text": word["text"],
                "bbox": word["bbox"]
            })

        # -------------------------
        # FINAL RESPONSE PER PAGE
        # -------------------------
        response_pages.append({
            "page": page_num + 1,
            "blocks": blocks,
            "logical_grid": logical_grid,
            "pixel_grid": pixel_grid
        })

    return {
        "pages": response_pages
    }
