"""
Paper Research Agent - Learn from arXiv, Semantic Scholar, and OpenAlex.
"""
import httpx
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from .base import BaseAgent, AgentContext
from .registry import AgentRegistry
from src.memory.store import associative_store
from src.memory.models import MemoryItem
from src.config import settings


@AgentRegistry.register("paper_researcher")
class PaperResearchAgent(BaseAgent):
    """Search and learn from academic papers."""

    ARXIV_URL = "http://export.arxiv.org/api/query"
    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1"
    OPENALEX_URL = "https://api.openalex.org"
    TIMEOUT = 30.0

    async def execute(
        self,
        context: AgentContext,
        query: str,
        source: str = "all",
        max_results: int = 5,
        store_in_memory: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Search papers and store in memory."""
        results: List[Dict] = []

        if source in ["arxiv", "all"]:
            results.extend(await self._search_arxiv(query, max_results))
        if source in ["semantic", "all"]:
            results.extend(await self._search_semantic_scholar(query, max_results))
        if source in ["openalex", "all"]:
            results.extend(await self._search_openalex(query, max_results))

        unique_results = self._deduplicate(results)

        if store_in_memory:
            for paper in unique_results:
                self._store_paper(paper)

        return {
            "query": query,
            "source": source,
            "results": unique_results,
            "count": len(unique_results)
        }

    async def _search_arxiv(self, query: str, max_results: int) -> List[Dict]:
        """Search arXiv - no API key needed."""
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                response = await client.get(self.ARXIV_URL, params=params)
                response.raise_for_status()
                return self._parse_arxiv(response.text)
            except Exception as e:
                return [{"error": f"arXiv error: {e}", "source": "arxiv"}]

    def _parse_arxiv(self, xml_text: str) -> List[Dict]:
        """Parse arXiv Atom feed."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", namespace):
            try:
                arxiv_id = entry.find("atom:id", namespace).text
                if arxiv_id:
                    arxiv_id = arxiv_id.replace("http://arxiv.org/abs/", "")
                title_elem = entry.find("atom:title", namespace)
                title = title_elem.text if title_elem is not None else "No title"
                summary_elem = entry.find("atom:summary", namespace)
                summary = summary_elem.text if summary_elem is not None else ""
                published_elem = entry.find("atom:published", namespace)
                published = published_elem.text if published_elem is not None else ""
                authors = []
                for author in entry.findall("atom:author", namespace):
                    name_elem = author.find("atom:name", namespace)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text)
                papers.append({
                    "source": "arxiv",
                    "id": f"arxiv:{arxiv_id}",
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "abstract": summary,
                    "authors": authors,
                    "published": published,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                })
            except Exception:
                continue
        return papers

    async def _search_semantic_scholar(self, query: str, max_results: int) -> List[Dict]:
        """Search Semantic Scholar."""
        headers = {}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key
        params = {
            "query": query,
            "limit": max_results,
            "fields": "paperId,title,abstract,authors,year,venue,doi,url"
        }
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                response = await client.get(
                    f"{self.SEMANTIC_SCHOLAR_URL}/paper/search",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return [self._format_semantic(p) for p in data.get("data", [])]
            except Exception as e:
                return [{"error": f"Semantic Scholar error: {e}", "source": "semantic"}]

    def _format_semantic(self, paper: Dict) -> Dict:
        """Format Semantic Scholar paper."""
        authors = [a.get("name") for a in paper.get("authors", []) if a and a.get("name")]
        return {
            "source": "semantic_scholar",
            "id": f"semantic:{paper.get('paperId')}",
            "semantic_id": paper.get("paperId"),
            "title": paper.get("title", "No title"),
            "abstract": paper.get("abstract", ""),
            "authors": authors,
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "doi": paper.get("doi"),
            "url": paper.get("url")
        }

    async def _search_openalex(self, query: str, max_results: int) -> List[Dict]:
        """Search OpenAlex - no API key needed."""
        params = {
            "search": query,
            "per-page": max_results,
            "filter": "type:work",
            "select": "id,title,abstract,authorships,publication_year,doi,url"
        }
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                response = await client.get(f"{self.OPENALEX_URL}/works", params=params)
                response.raise_for_status()
                data = response.json()
                return [self._format_openalex(p) for p in data.get("results", [])]
            except Exception as e:
                return [{"error": f"OpenAlex error: {e}", "source": "openalex"}]

    def _format_openalex(self, paper: Dict) -> Dict:
        """Format OpenAlex paper."""
        authors = []
        for authorship in paper.get("authorships", []):
            author = authorship.get("author", {})
            display_name = author.get("display_name")
            if display_name:
                authors.append(display_name)
        return {
            "source": "openalex",
            "id": f"openalex:{paper.get('id')}",
            "openalex_id": paper.get("id"),
            "title": paper.get("title", "No title"),
            "abstract": paper.get("abstract", ""),
            "authors": authors,
            "year": paper.get("publication_year"),
            "doi": paper.get("doi"),
            "url": paper.get("url")
        }

    def _deduplicate(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicates by DOI or ID."""
        seen: set = set()
        unique: List[Dict] = []
        for p in papers:
            key = p.get("doi") or p.get("arxiv_id") or p.get("semantic_id") or p.get("openalex_id") or p.get("id")
            if key and key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    def _store_paper(self, paper: Dict) -> None:
        """Store paper in associative memory."""
        try:
            tags = ["research", "academic", paper.get("source", "paper")]
            if paper.get("authors"):
                tags.extend(paper["authors"][:3])
            if paper.get("year"):
                tags.append(str(paper["year"]))

            content = paper.get("abstract") or ""
            if paper.get("url"):
                content += "\n\nURL: " + paper.get("url")

            item = MemoryItem(
                title=paper.get("title", "Untitled Paper"),
                content=content,
                tags=tags,
                metadata={
                    "source": paper.get("source"),
                    "paper_id": paper.get("id"),
                    "authors": paper.get("authors"),
                    "year": paper.get("year"),
                    "url": paper.get("url"),
                    "doi": paper.get("doi")
                }
            )
            associative_store.add(item)
        except Exception:
            pass
