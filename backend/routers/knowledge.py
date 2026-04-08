"""Offline Knowledge Base — index your docs, notes, PDFs, code repos."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from typing import Optional
import hashlib
import re
import json

from ..database import get_db, KnowledgeItem, AIInteraction
from ..config import KNOWLEDGE_DIR
from ..providers.registry import get_registry

router = APIRouter()


def simple_search(content: str, query: str) -> float:
    """Simple relevance score based on query term frequency."""
    query_terms = query.lower().split()
    content_lower = content.lower()
    matches = sum(content_lower.count(term) for term in query_terms)
    return matches / max(len(query_terms), 1)


class AskRequest(BaseModel):
    question: str
    doc_filter: Optional[str] = None  # Optional filename filter


@router.post("/ask")
async def ask_knowledge_base(req: AskRequest, db=Depends(get_db)):
    """Ask a question to the knowledge base using RAG with AI synthesis."""
    # Search knowledge base for relevant docs
    result = await db.execute(select(KnowledgeItem))
    items = result.scalars().all()

    scored = []
    for item in items:
        # Apply optional filename filter
        if req.doc_filter and req.doc_filter.lower() not in item.filename.lower():
            continue

        score = simple_search(item.content, req.question)
        if score > 0:
            scored.append({
                "id": item.id,
                "filename": item.filename,
                "content": item.content,
                "relevance": score,
            })

    scored.sort(key=lambda x: x["relevance"], reverse=True)
    top_docs = scored[:3]

    if not top_docs:
        return {
            "question": req.question,
            "answer": "No relevant documents found in knowledge base.",
            "sources": [],
            "confidence": 0.0,
        }

    # Build context from top results
    context_parts = []
    sources = []
    for doc in top_docs:
        context_parts.append(f"[{doc['filename']}]\n{doc['content'][:500]}...")
        sources.append({
            "id": doc["id"],
            "filename": doc["filename"],
            "relevance": round(doc["relevance"], 2),
        })

    context = "\n\n---\n\n".join(context_parts)

    # Get an available AI provider
    registry = get_registry()
    if not registry:
        return {
            "question": req.question,
            "answer": "No AI providers available to synthesize answer.",
            "sources": sources,
            "confidence": 0.0,
        }

    # Try providers in order: ollama, anthropic, openai, google
    provider_name = None
    provider = None
    for pname in ["ollama", "anthropic", "openai", "google"]:
        if pname in registry:
            p = registry[pname]
            try:
                if await p.is_available():
                    provider_name = pname
                    provider = p
                    break
            except Exception:
                continue

    if not provider:
        return {
            "question": req.question,
            "answer": "No available AI provider to synthesize answer.",
            "sources": sources,
            "confidence": 0.0,
        }

    # Build synthesis prompt
    synthesis_prompt = f"""Based on the following knowledge base documents, answer this question:

Question: {req.question}

Knowledge Base:
{context}

Provide a concise, factual answer based only on the documents above. Cite specific documents by filename."""

    try:
        models = await provider.list_models()
        if not models:
            return {
                "question": req.question,
                "answer": "AI provider has no available models.",
                "sources": sources,
                "confidence": 0.0,
            }

        model = models[0]
        response = await provider.complete(synthesis_prompt, model)

        # Log interaction (with error handling for missing tables)
        try:
            interaction = AIInteraction(
                provider=provider_name,
                model=model,
                prompt=synthesis_prompt,
                response=response.content,
                tokens_used=response.tokens_in + response.tokens_out,
                cost_usd=response.cost_usd,
            )
            db.add(interaction)
            await db.commit()
        except Exception as e:
            # Log error but don't fail the request if database isn't initialized
            pass

        return {
            "question": req.question,
            "answer": response.content,
            "sources": sources,
            "confidence": 0.8 if len(top_docs) >= 2 else 0.6,
            "provider": provider_name,
            "model": model,
        }

    except Exception as e:
        return {
            "question": req.question,
            "answer": f"Error generating answer: {str(e)}",
            "sources": sources,
            "confidence": 0.0,
        }


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
        item_metadata={"size": len(content), "type": file.content_type},
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


@router.get("")
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
            "metadata": item.item_metadata,
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
