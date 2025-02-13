from fastapi import FastAPI, BackgroundTasks
from .api_routes import router
from .dependencies import get_logger_dep
import asyncio
import httpx
import time

app = FastAPI(title="Fact-Checking Service")

async def poll_firebase():
    """Background task that polls Firebase for new videos every 5 seconds"""
    logger = get_logger_dep()
    base_url = "http://localhost:8000"
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                # Get list of videos
                response = await client.get(f"{base_url}/videos")
                if response.status_code == 200:
                    videos = response.json()
                    
                    # Process each unprocessed video
                    for video in videos:
                        status = video.get("status", "").lower()
                        if status not in ["processed", "in_progress"]:
                            vid = video.get("video_id")
                            if vid:
                                logger.info({"event": "processing_video", "video_id": vid})
                                try:
                                    await client.post(f"{base_url}/videos/{vid}/process")
                                except Exception as e:
                                    logger.error({"event": "video_processing_error", "video_id": vid, "error": str(e)})
                
        except Exception as e:
            logger.error({"event": "polling_error", "error": str(e)})
        
        # Wait 5 seconds before next poll
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    logger = get_logger_dep()
    logger.info({"event": "startup", "message": "App starting..."})
    
    # Start the background polling task
    asyncio.create_task(poll_firebase())

app.include_router(router)