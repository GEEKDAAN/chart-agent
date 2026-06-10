from fastapi import APIRouter

from app.schemas.chart import ChartAgentRequest, ChartAgentResponse
from app.services.chart_agent import run_chart_agent

router = APIRouter(prefix="/chart-agent", tags=["chart-agent"])


@router.post("/chat", response_model=ChartAgentResponse)
def chat(request: ChartAgentRequest) -> ChartAgentResponse:
    return run_chart_agent(request)
