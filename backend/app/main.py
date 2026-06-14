from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chart_agent import router as chart_agent_router
from app.routers.copilotkit import router as copilotkit_router

app = FastAPI(title="chart-agent API", version="0.10.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):517\d$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chart_agent_router)
app.include_router(copilotkit_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
