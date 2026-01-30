import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TaskType(str, Enum):
    """Supported task types"""
    DATA_PROCESSING = "data_processing"
    COMPUTATION = "computation"
    ANALYSIS = "analysis"
    SIMULATION = "simulation"

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskRequest(BaseModel):
    """Task request model"""
    task_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    timeout: Optional[int] = Field(default=300, description="Timeout in seconds")

class TaskResponse(BaseModel):
    """Task response model"""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None

class TaskExecution:
    """Internal task execution tracking"""
    def __init__(self, request: TaskRequest):
        self.request = request
        self.status = TaskStatus.PENDING
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.execution_time: Optional[float] = None

class TestAgent:
    """Production-ready FastAPI agent for task execution"""
    
    def __init__(self):
        self.agent_id = "test-agent-001"
        self.version = "1.0.0"
        self.start_time = time.time()
        self.tasks: Dict[str, TaskExecution] = {}
        self.max_concurrent_tasks = 10
        self.task_semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.is_initialized = False
        self.task_counter = 0
        
    async def initialize(self):
        """Initialize the agent"""
        try:
            logger.info(f"Initializing {self.agent_id} v{self.version}")
            # Add any initialization logic here (database connections, external services, etc.)
            await asyncio.sleep(0.1)  # Simulate initialization time
            self.is_initialized = True
            logger.info("Agent initialization completed")
        except Exception as e:
            logger.error(f"Agent initialization failed: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            logger.info("Starting agent cleanup")
            # Cancel any running tasks
            for task_id, task_exec in self.tasks.items():
                if task_exec.status == TaskStatus.RUNNING:
                    task_exec.status = TaskStatus.CANCELLED
                    task_exec.completed_at = datetime.now(timezone.utc)
                    logger.info(f"Cancelled task {task_id}")
            
            self.is_initialized = False
            logger.info("Agent cleanup completed")
        except Exception as e:
            logger.error(f"Agent cleanup failed: {str(e)}")
    
    async def is_healthy(self) -> bool:
        """Check if agent is healthy"""
        try:
            # Basic health checks
            if not self.is_initialized:
                return False
            
            # Check if we're not overwhelmed with tasks
            running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
            if running_tasks > self.max_concurrent_tasks:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status and metrics"""
        uptime = time.time() - self.start_time
        
        # Calculate task statistics
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
        
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "status": "healthy" if await self.is_healthy() else "unhealthy",
            "uptime": uptime,
            "initialized": self.is_initialized,
            "metrics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "running_tasks": running_tasks,
                "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            "resources": {
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "available_slots": self.max_concurrent_tasks - running_tasks
            },
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Execute a task"""
        if not self.is_initialized:
            raise RuntimeError("Agent not initialized")
        
        task_exec = TaskExecution(request)
        self.tasks[request.task_id] = task_exec
        self.task_counter += 1
        
        try:
            async with self.task_semaphore:
                task_exec.status = TaskStatus.RUNNING
                logger.info(f"Starting task {request.task_id} of type {request.task_type}")
                
                # Execute the actual task
                result = await self._process_task(request)
                
                task_exec.status = TaskStatus.COMPLETED
                task_exec.result = result
                task_exec.completed_at = datetime.now(timezone.utc)
                task_exec.execution_time = (task_exec.completed_at - task_exec.started_at).total_seconds()
                
                logger.info(f"Task {request.task_id} completed successfully")
                
        except Exception as e:
            task_exec.status = TaskStatus.FAILED
            task_exec.error = str(e)
            task_exec.completed_at = datetime.now(timezone.utc)
            task_exec.execution_time = (task_exec.completed_at - task_exec.started_at).total_seconds()
            
            logger.error(f"Task {request.task_id} failed: {str(e)}")
        
        return TaskResponse(
            task_id=request.task_id,
            status=task_exec.status,
            result=task_exec.result,
            error=task_exec.error,
            started_at=task_exec.started_at,
            completed_at=task_exec.completed_at,
            execution_time=task_exec.execution_time
        )
    
    async def _process_task(self, request: TaskRequest) -> Dict[str, Any]:
        """Process different types of tasks"""
        try:
            if request.task_type == TaskType.DATA_PROCESSING:
                return await self._process_data_task(request.parameters)
            elif request.task_type == TaskType.COMPUTATION:
                return await self._process_computation_task(request.parameters)
            elif request.task_type == TaskType.ANALYSIS:
                return await self._process_analysis_task(request.parameters)
            elif request.task_type == TaskType.SIMULATION:
                return await self._process_simulation_task(request.parameters)
            else:
                raise ValueError(f"Unsupported task type: {request.task_type}")
        
        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}")
            raise
    
    async def _process_data_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process data processing task"""
        # Simulate data processing
        data_size = parameters.get("data_size", 100)
        await asyncio.sleep(min(data_size / 100, 5))  # Simulate processing time
        
        return {
            "processed_records": data_size,
            "output_format": parameters.get("output_format", "json"),
            "timestamp": datetime.now(timezone.utc),
            "message": "Data processing completed successfully"
        }
    
    async def _process_computation_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process computation task"""
        # Simulate computation
        iterations = parameters.get("iterations", 1000)
        await asyncio.sleep(min(iterations / 1000, 3))  # Simulate computation time
        
        # Simple computation example
        result_value = sum(range(min(iterations, 10000)))
        
        return {
            "computation_result": result_value,
            "iterations": iterations,
            "algorithm": parameters.get("algorithm", "default"),
            "timestamp": datetime.now(timezone.utc),
            "message": "Computation completed successfully"
        }
    
    async def _process_analysis_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis task"""
        # Simulate analysis
        dataset_name = parameters.get("dataset", "default")
        await asyncio.sleep(2)  # Simulate analysis time
        
        return {
            "analysis_type": parameters.get("analysis_type", "statistical"),
            "dataset": dataset_name,
            "insights": [
                "Pattern A detected with 85% confidence",
                "Anomaly detected in region B",
                "Trend analysis shows upward movement"
            ],
            "confidence_score": 0.87,
            "timestamp": datetime.now(timezone.utc),
            "message": "Analysis completed successfully"
        }
    
    async def _process_simulation_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process simulation task"""
        # Simulate simulation
        duration = parameters.get("duration", 10)
        await asyncio.sleep(min(duration / 10, 4))  # Simulate simulation time
        
        return {
            "simulation_type": parameters.get("simulation_type", "monte_carlo"),
            "duration": duration,
            "results": {
                "success_rate": 0.93,
                "average_value": 42.7,
                "standard_deviation": 8.3
            },
            "iterations": duration * 100,
            "timestamp": datetime.now(timezone.utc),
            "message": "Simulation completed successfully"
        }
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task_exec = self.tasks.get(task_id)
        if not task_exec:
            return None
        
        return {
            "task_id": task_id,
            "task_type": task_exec.request.task