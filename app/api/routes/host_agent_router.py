from fastapi import APIRouter, HTTPException, Depends, Request
from app.agent.host.multiagent.host_agent import HostAgent
from app.agent.host.multiagent.remote_agent_connection import TaskCallbackArg
from app.common.types import AgentCard, Task, TaskState, Message, TextPart
from app.api.services.notification_service import NotificationService, PushNotificationSenderAuth
import logging
import re
import json
from datetime import datetime
from typing import Dict, Optional, List, Any
from app.core.settings.agent_address import remote_agent_address_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/host", tags=["host_agent"])

# Initialize PushNotificationSenderAuth
sender_auth = PushNotificationSenderAuth()
sender_auth.generate_jwk()

# Initialize NotificationService
notification_service = NotificationService(sender_auth)

# Dictionary to store thought process history
thought_process_history: Dict[str, str] = {}
# Dictionary to store current agent per task
current_agent_info: Dict[str, Dict[str, Any]] = {}

async def handle_task_updates(update: TaskCallbackArg, agent_card: AgentCard) -> Task:
    """
    Handle task updates and send notifications to clients.
    
    This function processes updates received from the host agent's task execution,
    extracts thought processes, tracks agent changes, and sends appropriate
    notifications to registered clients.
    
    Args:
        update: Task update data from the agent
        agent_card: Information about the agent that generated the update
        
    Returns:
        The updated Task object
    """
    try:
        # Extract task ID and state
        task_id = getattr(update, "id", None)
        
        if not task_id:
            logger.warning("Received update without task ID")
            return update
            
        # Extract task state
        task_state = None
        if hasattr(update, "status") and hasattr(update.status, "state"):
            task_state = update.status.state
        
        # Process agent information
        agent_info = {
            "name": agent_card.name,
            "description": agent_card.description,
            "skills": [
                {"name": skill.name, "description": skill.description} 
                for skill in agent_card.skills
            ] if hasattr(agent_card, "skills") and agent_card.skills else []
        }
        
        # Check if there's an agent change
        agent_changed = False
        if task_id not in current_agent_info or current_agent_info[task_id].get("name") != agent_info["name"]:
            current_agent_info[task_id] = agent_info
            agent_changed = True
            
            # Send agent change notification
            await notification_service.send_agent_change_notification(task_id, agent_info)
        
        # Extract thought process from message
        thought_process = ""
        if hasattr(update, "status") and hasattr(update.status, "message") and update.status.message:
            message_text = ""
            for part in update.status.message.parts:
                if hasattr(part, "text") and part.text:
                    message_text += part.text
            
            # Extract thought process using pattern matching
            thought_match = re.search(r'(?:Thought process:|Reasoning:|Thinking:|I need to|Let me think about)([^<]*)', 
                                     message_text, re.IGNORECASE)
            if thought_match:
                thought_process = thought_match.group(1).strip()
                
                # Update thought process history
                if task_id not in thought_process_history:
                    thought_process_history[task_id] = thought_process
                else:
                    # Append new thought only if it's different from previous
                    if thought_process and thought_process not in thought_process_history[task_id]:
                        thought_process_history[task_id] += f"\n{thought_process}"
                
                # Send thought process update notification
                if thought_process:
                    await notification_service.send_thought_process_update(
                        task_id, thought_process_history[task_id]
                    )
        
        # Handle task completion
        if task_state == TaskState.COMPLETED:
            # Prepare result data
            result = {
                "state": "completed",
                "agent": agent_info["name"],
                "completion_time": datetime.now().isoformat()
            }
            
            # Extract final response or artifacts if available
            if hasattr(update, "status") and hasattr(update.status, "message") and update.status.message:
                message_parts = []
                for part in update.status.message.parts:
                    if hasattr(part, "text") and part.text:
                        message_parts.append(part.text)
                    elif hasattr(part, "data") and part.data:
                        message_parts.append(json.dumps(part.data))
                        
                if message_parts:
                    result["response"] = "\n".join(message_parts)
            
            # Include artifacts if available
            if hasattr(update, "artifacts") and update.artifacts:
                artifacts = []
                for artifact in update.artifacts:
                    artifact_data = {
                        "name": artifact.name if hasattr(artifact, "name") else "unnamed",
                        "description": artifact.description if hasattr(artifact, "description") else "",
                        "content": []
                    }
                    
                    for part in artifact.parts:
                        if hasattr(part, "text") and part.text:
                            artifact_data["content"].append({"type": "text", "value": part.text})
                        elif hasattr(part, "data") and part.data:
                            artifact_data["content"].append({"type": "data", "value": part.data})
                    
                    artifacts.append(artifact_data)
                
                if artifacts:
                    result["artifacts"] = artifacts
            
            # Send task completion notification
            await notification_service.send_task_completion_notification(task_id, result)
            
            # Clean up memory
            if task_id in thought_process_history:
                del thought_process_history[task_id]
            if task_id in current_agent_info:
                del current_agent_info[task_id]
        
        return update
        
    except Exception as e:
        logger.exception(f"Error processing task update: {str(e)}")
        return update

# Initialize the host agent with our callback function
try:
    host_agent = HostAgent(
        remote_agent_addresses=remote_agent_address_settings.REMOTE_AGENT_ADDRESS,
        task_callback=handle_task_updates
    )
    host_agent.create_agent()
except Exception as e:
    logger.error(f"Error creating host agent: {e}")
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{agent_name}")
async def create_task(request: Request, agent_name: str):
    """
    Create a new task for the specified agent.
    
    Args:
        request: The HTTP request
        agent_name: Name of the agent to handle the task
        
    Returns:
        Task object with task ID and status
    """
    task_data = await request.json()
    message = task_data.get("message", "")
    
    # Generate a task
    task = await host_agent.send_task(
        agent_name=agent_name,
        message=message,
        tool_context=None  # This would need to be adapted to your actual implementation
    )
    
    # Register for notifications if URL provided
    if "notification_url" in task_data:
        notification_service.register_task_notification(
            task_id=task.id, 
            notification_url=task_data["notification_url"]
        )
    
    return task

@router.get("/agents")
async def list_agents():
    """List all available agents."""
    return host_agent.list_remote_agents()
