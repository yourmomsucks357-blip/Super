import os
import uvicorn
from src.agents.examples import *       # noqa: registers echo/sleep/compute
from src.agents.chat_agents import *    # noqa: registers assistant/router
from src.agents.youtube_agent import *  # noqa: registers youtube_learner
from src.agents.paper_research_agent import *  # noqa: registers paper_researcher
from src.api.main import app
from src.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=port,
        reload=settings.debug,
    )
