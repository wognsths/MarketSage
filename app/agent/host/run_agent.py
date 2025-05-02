from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.agent.host.multiagent.host_agent import HostAgent
from app.api.routes.host_agent_router import router as host_agent_router
from app.api.services.notification_service import NotificationService, PushNotificationSenderAuth
from app.core.settings.agent_address import remote_agent_address_settings
import logging
import uvicorn
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def startup():
    logger.info("MarketSage Host Agent service started.")
    logger.info(f"Registered agent's address: {remote_agent_address_settings.REMOTE_AGENT_ADDRESS}")
def shutdown():
    logger.info("MarketSage Host Agent service stopped.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()

app = FastAPI(
    title="MarketSage Host Agent",
    description="MarketSage Host agent API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(host_agent_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "host-agent"}


def main():
    """Main entry point for the host agent application.
    This function is used by the poetry script to start the host agent service.
    """
    port = int(os.getenv("HOST_AGENT_PORT", 10000))
    
    uvicorn.run(
        "app.agent.host.run_agent:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "production").lower() == "development",
        log_level="info"
    )
    
    logger.info(f"MarketSage Host Agent API - http://localhost:{port}")


if __name__ == "__main__":
    main()
    
    logger.info(f"MarketSage Host Agent API - http://localhost:{port}")

