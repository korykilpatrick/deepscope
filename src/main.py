from fastapi import FastAPI
from .api_routes import router

app = FastAPI()

app.include_router(router)