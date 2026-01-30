from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from agent import TestAgent, TaskRequest, TaskResponse
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Global agent instance
agent_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global agent_instance
    
    # Startup
    logger.info("Initializing test-agent-001...")
    agent_instance = TestAgent()
    await agent_instance.initialize()
    logger.info("Agent initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down test-agent-001...")
    if agent_instance:
        await agent_instance.cleanup()
    logger.info("Agent shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Test Agent 001",
    description="A production-ready FastAPI agent for task execution",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if agent_instance and await agent_instance.is_healthy():
            return {
                "status": "healthy",
                "agent_id": "test-agent-001",
                "version": "1.0.0"
            }
        else:
            raise HTTPException(status_code=503, detail="Agent unhealthy")
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Health check failed")

@app.get("/status")
async def get_status():
    """Get agent status and metrics"""
    try:
        if not agent_instance:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        status = await agent_instance.get_status()
        return status
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")

@app.post("/run", response_model=TaskResponse)
async def run_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Execute a task"""
    try:
        if not agent_instance:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        logger.info(f"Received task: {task_request.task_type} - {task_request.task_id}")
        
        # Execute task
        response = await agent_instance.execute_task(task_request)
        
        # Add cleanup to background tasks if needed
        if response.task_id:
            background_tasks.add_task(agent_instance.cleanup_task, response.task_id)
        
        return response
        
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    try:
        if not agent_instance:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        task_status = await agent_instance.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get task status")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )