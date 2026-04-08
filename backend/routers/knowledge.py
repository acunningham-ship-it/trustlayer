"""Offline Knowledge Base — index your docs, notes, PDFs, code repos."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from typing import Optional
import hashlib
import re

from ..database import get_db, KnowledgeItem
from ..config import KNOWLEDGE_DIR

router = APIRouter()


def simple_search(content: str, query: str) -> float:
    """Simple relevance score based on query term frequency."""
    query_terms = query.lower().split()
    content_lower = content.lower()
    matches = sum(content_lower.count(term) for term in query_terms)
    return matches / max(len(query_terms), 1)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db=Depends(get_db)):
    """Upload and index a document into the knowledge base."""
    content = await file.read()

    # Handle different file types
    if file.filename.endswith(".pdf"):
        try:
            import pdfminer.high_level
            import io
            text = pdfminer.high_level.extract_text(io.BytesIO(content))
        except ImportError:
            text = content.decode("utf-8", errors="ignore")
    else:
        text = content.decode("utf-8", errors="ignore")

    # Save file
    dest = KNOWLEDGE_DIR / file.filename
    dest.write_bytes(content)

    # Index in DB
    item = KnowledgeItem(
        filename=file.filename,
        content=text,
        metadata={"size": len(content), "type": file.content_type},
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "id": item.id,
        "filename": file.filename,
        "words": len(text.split()),
        "indexed": True,
    }


@router.get("/search")
async def search_knowledge(q: str, limit: int = 5, db=Depends(get_db)):
    """Search your knowledge base."""
    result = await db.execute(select(KnowledgeItem))
    items = result.scalars().all()

    scored = []
    for item in items:
        score = simple_search(item.content, q)
        if score > 0:
            # Extract relevant snippet
            idx = item.content.lower().find(q.lower().split()[0])
            snippet = item.content[max(0, idx - 100): idx + 200] if idx >= 0 else item.content[:200]
            scored.append({
                "id": item.id,
                "filename": item.filename,
                "snippet": snippet.strip(),
                "relevance": score,
            })

    scored.sort(key=lambda x: x["relevance"], reverse=True)
    return scored[:limit]


@router.get("/")
async def list_knowledge(db=Depends(get_db)):
    """List all indexed documents."""
    result = await db.execute(select(KnowledgeItem))
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "words": len(item.content.split()),
            "indexed_at": item.indexed_at.isoformat(),
            "metadata": item.metadata,
        }
        for item in items
    ]


@router.delete("/{item_id}")
async def delete_knowledge(item_id: str, db=Depends(get_db)):
    """Remove a document from the knowledge base."""
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    file_path = KNOWLEDGE_DIR / item.filename
    if file_path.exists():
        file_path.unlink()
    await db.delete(item)
    await db.commit()
    return {"deleted": item_id}
