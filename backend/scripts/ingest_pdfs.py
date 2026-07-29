import asyncio
import re
import sys
from pathlib import Path

from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "BNS_queries" / "BNS_QUERIES"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def extract_pdf_text_pdfplumber(pdf_path: str) -> list[str]:
    import pdfplumber

    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            pages_text.append(t)
    return pages_text


def extract_pdf_text_pypdf2(pdf_path: str) -> list[str]:
    import PyPDF2

    pages_text = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
    return pages_text


def get_chapter_pages(pages_text: list[str]) -> list[dict]:
    roman = r"(?:M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
    chapter_starts = []
    for i, text in enumerate(pages_text):
        for m in re.finditer(rf"^\s*CHAPTER\s+({roman})\s*$", text, re.MULTILINE):
            chapter_starts.append((i + 1, m.group(1)))

    full_text_starts = []
    seen_at_right_positions = {}
    for page_num, ch_num in chapter_starts:
        if page_num < 74:
            continue
        if ch_num in seen_at_right_positions:
            continue
        seen_at_right_positions[ch_num] = page_num
        full_text_starts.append({"chapter": f"CHAPTER {ch_num}", "page": page_num})

    full_text_starts.sort(key=lambda r: r["page"])
    return full_text_starts


def clean_text(text: str) -> str:
    text = re.sub(r"\uf0b7", "- ", text)
    text = re.sub(r"CHAPTER\s+\w+\s+-+\s*", "", text)
    text = re.sub(r"HomePage|S\.\s*\d+\.?\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r" {3,}", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def main():
    setup_logging()

    logger.info("extracting_bns2023_pdf")
    try:
        pages_text = extract_pdf_text_pdfplumber(str(ROOT_DIR / "BNS2023.pdf"))
    except Exception as e:
        logger.warning("pdfplumber_failed_try_pypdf2", error=str(e))
        pages_text = extract_pdf_text_pypdf2(str(ROOT_DIR / "BNS2023.pdf"))

    logger.info("extracted_pages", count=len(pages_text))

    chapters = get_chapter_pages(pages_text)
    logger.info("chapters_found", count=len(chapters))
    for ch in chapters:
        print(f"  {ch['chapter']} (page {ch['page']})")

    all_chunks = []
    chunk_id = 0
    for i, ch in enumerate(chapters):
        start_page = ch["page"] - 1
        end_page = chapters[i + 1]["page"] - 1 if i + 1 < len(chapters) else len(pages_text)

        raw_text = "\n".join(pages_text[start_page:end_page])
        cleaned = clean_text(raw_text)
        if len(cleaned) < 100:
            continue

        all_chunks.append(
            {
                "id": f"bns_pdf_{i + 1:03d}",
                "text": cleaned,
                "metadata": {
                    "source": "bns_2023_pdf",
                    "type": "chapter",
                    "chapter": ch["chapter"],
                    "pages": f"{ch['page']}-{min(end_page + 1, len(pages_text))}",
                    "chunk": chunk_id,
                },
            }
        )
        chunk_id += 1
        print(f"  {ch['chapter']}: {len(cleaned):>6} chars")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for c in all_chunks:
        lines.append(c["text"])
        lines.append("")

    final_text = "\n".join(lines)
    output_path = DATA_DIR / "bns_full_pdf.txt"
    output_path.write_text(final_text, encoding="utf-8")
    logger.info("saved_pdf_text", path=str(output_path), chars=len(final_text), chunks=len(all_chunks))

    logger.info("extraction_complete", path=str(output_path), chars=len(final_text), chapters=len(all_chunks))

    if "--ingest" in sys.argv:
        await ingest_into_chromadb(all_chunks)


async def ingest_into_chromadb(chunks: list[dict]):
    import chromadb
    from app.core.settings import get_settings
    from app.integrations.ollama import get_ollama_client

    settings = get_settings()
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        headers={"Authorization": f"Bearer {settings.chroma_token}"},
    )
    try:
        collection = client.get_collection("bnsai_rag_pdf")
    except Exception:
        collection = client.create_collection("bnsai_rag_pdf")

    existing = collection.count()
    if existing > 0:
        logger.info("recreating_collection", collection="bnsai_rag_pdf", existing=existing)
        client.delete_collection("bnsai_rag_pdf")
        collection = client.create_collection("bnsai_rag_pdf")

    ollama = get_ollama_client()
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        resp = await ollama.post(
            "/api/embed",
            json={"model": "nomic-embed-text", "input": texts},
        )
        resp.raise_for_status()
        embeddings = resp.json()["embeddings"]
        collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)
        logger.info("chroma_batch_ingested", batch=i // batch_size + 1, count=len(batch))

    logger.info("pdf_ingestion_complete", collection="bnsai_rag_pdf", chapters=len(chunks))


if __name__ == "__main__":
    asyncio.run(main())
