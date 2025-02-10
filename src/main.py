from fastapi import FastAPI
from src.api_routes import router

app = FastAPI(title="Financial Fact-Checking Service")

# Include routes from api_routes.py
app.include_router(router)

# You could add an event handler here for on_startup, if needed:
# @app.on_event("startup")
# async def startup_event():
#     # e.g., subscribe to a Firebase listener or do any one-time init
#     pass