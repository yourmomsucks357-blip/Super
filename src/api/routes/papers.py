"""
Paper Research API - Search arXiv, Semantic Scholar, OpenAlex.
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from src.agents.paper_research_agent import PaperResearchAgent

router = APIRouter(prefix="/papers", tags=["papers", "research"])


class PaperSearchRequest(BaseModel):
    """Request model for paper search."""
    query: str = Query(..., min_length=3, max_length=500,
                       description="Search query for academic papers")
    source: str = Query("all",
                       description="Source: arxiv, semantic, openalex, or all")
    max_results: int = Query(5, ge=1, le=50,
                           description="Max results per source")
    store_in_memory: bool = Query(True,
                               description="Store results in memory for learning")


@router.post("/search")
async def search_papers(request: PaperSearchRequest) -> dict:
    """
    Search academic papers across arXiv, Semantic Scholar, and OpenAlex.
    """
    agent = PaperResearchAgent()
    result = await agent.execute(
        context=None,
        query=request.query,
        source=request.source,
        max_results=request.max_results,
        store_in_memory=request.store_in_memory
    )
    return result


@router.get("/search")
async def search_papers_get(
    query: str = Query(..., min_length=3, max_length=500),
    source: str = "all",
    max_results: int = 5,
    store_in_memory: bool = True
) -> dict:
    """
    GET endpoint for searching papers.
    """
    agent = PaperResearchAgent()
    result = await agent.execute(
        context=None,
        query=query,
        source=source,
        max_results=max_results,
        store_in_memory=store_in_memory
    )
    return result


@router.post("/arxiv")
async def search_arxiv(
    query: str = Query(..., min_length=3, max_length=500),
    max_results: int = 5,
    store_in_memory: bool = True
) -> dict:
    """Search arXiv papers only."""
    agent = PaperResearchAgent()
    result = await agent.execute(
        context=None,
        query=query,
        source="arxiv",
        max_results=max_results,
        store_in_memory=store_in_memory
    )
    return result


@router.post("/semantic")
async def search_semantic(
    query: str = Query(..., min_length=3, max_length=500),
    max_results: int = 5,
    store_in_memory: bool = True
) -> dict:
    """Search Semantic Scholar papers only."""
    agent = PaperResearchAgent()
    result = await agent.execute(
        context=None,
        query=query,
        source="semantic",
        max_results=max_results,
        store_in_memory=store_in_memory
    )
    return result


@router.post("/openalex")
async def search_openalex(
    query: str = Query(..., min_length=3, max_length=500),
    max_results: int = 5,
    store_in_memory: bool = True
) -> dict:
    """Search OpenAlex papers only."""
    agent = PaperResearchAgent()
    result = await agent.execute(
        context=None,
        query=query,
        source="openalex",
        max_results=max_results,
        store_in_memory=store_in_memory
    )
    return result
