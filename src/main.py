from fastapi import FastAPI
from .api_routes import router
from .dependencies import get_logger_dep

app = FastAPI(title="Fact-Checking Service")

@app.on_event("startup")
async def startup_event():
    logger = get_logger_dep()
    logger.info({"event": "startup", "message": "App starting..."})

app.include_router(router)