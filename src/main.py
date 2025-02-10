from fastapi import FastAPI
from src.api_routes import router

app = FastAPI(title="Fact-Checking Service")

app.include_router(router)

# If needed, add lifecycle events:
# @app.on_event("startup")
# async def startup_event():
#     pass