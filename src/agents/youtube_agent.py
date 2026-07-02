"""
YouTube Learning Agent — fetches a video transcript and stores it in
AssociativeMemory so the knowledge is available to the cognitive loop
and retrievable via the /memory API.
"""
import re
from typing import Any, List

from src.agents.base import AgentContext, BaseAgent
from src.agents.registry import AgentRegistry
from src.memory.models import MemoryItem
from src.memory.store import associative_store


def _extract_video_id(url_or_id: str) -> str:
    """Return the 11-char video ID from a URL or bare ID."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url_or_id)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract a YouTube video ID from: {url_or_id!r}")


@AgentRegistry.register("youtube_learner")
class YouTubeLearningAgent(BaseAgent):
    """
    Fetches the transcript of a YouTube video and stores it in
    AssociativeMemory so it is retrievable by the cognitive loop
    and visible in the Memory view of the UI.

    kwargs:
        url      (str)       – YouTube URL or 11-char video ID (required).
        title    (str)       – Optional custom title; defaults to video ID.
        language (str)       – Transcript language code, default "en".
        tags     (list[str]) – Extra tags to attach to the memory item.
    """

    async def execute(
        self,
        context: AgentContext,
        url: str = "",
        subject: str = "",
        title: str = "",
        language: str = "en",
        tags: List[str] = None,
        **kwargs,
    ) -> Any:
        if not url:
            return {"error": "'url' is required. Example: {\"url\": \"https://www.youtube.com/watch?v=VIDEO_ID\"}"}

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise RuntimeError(
                "youtube-transcript-api is not installed. "
                "Run: pip install youtube-transcript-api"
            )

        video_id = _extract_video_id(url)
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"

        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=[language])
        full_text = " ".join(entry.text for entry in transcript)

        # Subject is the primary retrieval key — stored as title + tag so the
        # memory retriever finds this knowledge when that topic is queried.
        effective_subject = subject or title or video_id
        subject_tags = [effective_subject] + (
            [t.strip() for t in effective_subject.replace("-", " ").split() if len(t.strip()) > 2]
        )

        item = MemoryItem(
            title=effective_subject,
            content=full_text,
            tags=list(dict.fromkeys(subject_tags + (tags or []) + ["youtube", f"video:{video_id}"])),
            metadata={
                "source":        "youtube",
                "video_id":      video_id,
                "url":           canonical_url,
                "language":      language,
                "segment_count": len(transcript),
                "subject":       effective_subject,
            },
        )
        associative_store.add(item)

        return {
            "video_id":          video_id,
            "url":               canonical_url,
            "memory_id":         item.item_id,
            "subject":           effective_subject,
            "title":             item.title,
            "characters_stored": len(full_text),
            "segments":          len(transcript),
            "tags":              item.tags,
        }
