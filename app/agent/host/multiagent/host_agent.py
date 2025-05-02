import sys
import asyncio
import functools
import json
import uuid
import threading
import time
import httpx
import logging
from typing import List, Optional, Callable

# Logging settings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from google.genai import types
import base64

from google.adk import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from .remote_agent_connection import (
    RemoteAgentConnections,
    TaskUpdateCallback
)
from app.common.client.card_resolver import A2ACardResolver
from app.common.types import (
    AgentCard,
    Message,
    TaskState,
    Task,
    TaskSendParams,
    TextPart,
    DataPart,
    Part,
    TaskStatusUpdateEvent,
)
from app.core.settings.llm_models import llm_models

class HostAgent:
    """
    The host agent.

    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work.
    """

    def __init__(
        self,
        remote_agent_addresses: List[str],
        task_callback: TaskUpdateCallback
    ):
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}

        for address in remote_agent_addresses:  ## address example: http://localhost:8001(db-agent)
            card_resolver = A2ACardResolver(address)
            card = card_resolver.get_agent_card() # JSON 반환 -> dict
            remote_connection = RemoteAgentConnections(card)
            self.remote_agent_connections[card.name] = remote_connection  # card name: db-agent, value: remote_connection
            self.cards[card.name] = card
        agent_info = []
        for remote_agent in self.list_remote_agents():
            agent_info.append(json.dumps(remote_agent))
        self.agents = '\n'.join(agent_info)
    
    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for remote_agent in self.list_remote_agents():  # 이미 initate된 경우 새로운 에이전트를 등록하는 방법
            agent_info.append(json.dumps(remote_agent))
        self.agents = '\n'.join(agent_info)

    def create_agent(self) -> Agent:
        return Agent(
            model=llm_models["available_agent"],
            name="host_agent",
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                "This agent orchestrates the decomposition of the user request into"
                " tasks that can be performed by the child agents."
            ),
            tools=[
                self.list_remote_agents,
                self.send_task,
            ],
        )
    
    def root_instruction(self, context: ReadonlyContext) -> str:
        current_agent = self.check_state(context)
        return f"""You are an expert task delegator.

Your role is to interpret user requests and delegate them to the most appropriate remote agents using tools only.

Discovery:
- Use the `list_remote_agents` tool to view available agents and their descriptions.

Execution:
- Use the `create_task` tool to assign tasks to remote agents.
- Always specify the agent name explicitly when responding to the user.

Monitoring:
- Use the `check_pending_task_states` tool to check the status of active tasks.

Guidelines:
- Do not generate responses yourself. Always rely on tools to fulfill requests.
- If the user input is vague or unclear, use the `ask_user` tool to ask for clarification.
- Unless the user request has a clearly-specified execution plan, request to the "planner-agent" to generate a structured task plan.

Focus on the most recent part of the conversation.

If there is an active agent, continue by sending the next message using `create_task`.

Available Agents:
{self.list_remote_agents()}

Current active agent: {current_agent['active_agent']}
"""
    def check_state(self, context: ReadonlyContext):
        state = context.state
        if ('session_id' in state and
            'session_active' in state and
            state['session_active'] and
            'agent' in state):
            return {"active_agent": f'{state["agent"]}'}
        return {"active_agent": "None"}
    
    def before_model_callback(self, callback_context: CallbackContext, llm_request):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
            state['session_active'] = True

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []
        
        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {"name": card.name, "description": card.description}
            )
        return remote_agent_info
    
    
    async def send_task(
            self,
            agent_name: str,
            message: str,
            tool_context: ToolContext):
        """Sends a task either streaming (if supported) or non-streaming.

        This will send a message to the remote agent named agent_name.

        Args:
        agent_name: The name of the agent to send the task to.
        message: The message to send to the agent for the task.
        tool_context: The tool context this method runs in.

        Yields:
        A dictionary of JSON data.
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")
        state = tool_context.state
        state['agent'] = agent_name
        card = self.cards[agent_name]
        client = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f"Client not available for {agent_name}")
        if 'task_id' in state:
            taskId = state['task_id']
        else:
            taskId = str(uuid.uuid4())
        sessionId = state['session_id']
        task: Task
        messageId = ""
        metadata = {}
        if 'input_message_metadata' in state:
            metadata.update(**state['input_message_metadata'])
            if 'message_id' in state['input_message_metadata']:
                messageId = state['input_message_metadata']['message_id']
        if not messageId:
            messageId = str(uuid.uuid4())
        metadata.update(**{'conversation_id': sessionId, 'message_id': messageId})
        request: TaskSendParams = TaskSendParams(
            id=taskId,
            sessionId=sessionId,
            message=Message(
                role="user",
                parts=[TextPart(text=message)],
                metadata=metadata,
            ),
            acceptedOutputModes=["text", "text/plain", "image/png"],
            # pushNotification=None,
            metadata={'conversation_id': sessionId},
        )
        task = await client.send_task(request, self.task_callback)
        # Assume completion unless a state returns that isn't complete
        state['session_active'] = task.status.state not in [
            TaskState.COMPLETED,
            TaskState.CANCELED,
            TaskState.FAILED,
            TaskState.UNKNOWN,
        ]
        if task.status.state == TaskState.INPUT_REQUIRED:
            # force user input back
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True
        elif task.status.state == TaskState.CANCELED:
            # Open question, should we return some info for cancellation instead
            raise ValueError(f"Agent {agent_name} task {task.id} is cancelled")
        elif task.status.state == TaskState.FAILED:
            # Raise error for failure
            raise ValueError(f"Agent {agent_name} task {task.id} failed")
        response = []
        if task.status.message:
            # Assume the info is in the task message.
            logger.info(f"Response received from {agent_name}. Task state: {task.status.state}")
            logger.info(f"Task message parts: {[p.type for p in task.status.message.parts if task.status.message and task.status.message.parts]}")
            response.extend(convert_parts(task.status.message.parts, tool_context))
        if task.artifacts:
            logger.info(f"Artifacts received from {agent_name}: {len(task.artifacts)}")
            for artifact in task.artifacts:
                logger.info(f"Artifact parts: {[p.type for p in artifact.parts]}")
                response.extend(convert_parts(artifact.parts, tool_context))

        if self.task_callback and response:
            from app.common.types import TaskStatusUpdateEvent, TaskStatus
            import datetime

            logger.info(f"Task callback triggered. Response content: {response}")
            self.task_callback(
                TaskStatusUpdateEvent(
                    id=task.id,
                    sessionId=task.sessionId,
                    status=TaskStatus(
                        state=task.status.state,
                        message=Message(
                            role="agent",
                            parts=[TextPart(text="\n".join(map(str, response)))]
                        ),
                        timestamp=datetime.datetime.now().isoformat()
                    )
                ),
                card
            )
        logger.info(f"send_task method completed. Response: {response}")
        return response
    
def convert_parts(parts: list[Part], tool_context: ToolContext):
    rval = []
    for p in parts:
        rval.append(convert_part(p, tool_context))
    return rval
    
def convert_part(part: Part, tool_context: ToolContext):
    if part.type == "text":
        return part.text
    elif part.type == "data":
        return part.data
    elif part.type == "file":
        # Repackage A2A FilePart to google.genai Blob
        # Currently not considering plain text as files    
        file_id = part.file.name
        file_bytes = base64.b64decode(part.file.bytes)    
        file_part = types.Part(
        inline_data=types.Blob(
            mime_type=part.file.mimeType,
            data=file_bytes))
        tool_context.save_artifact(file_id, file_part)
        tool_context.actions.skip_summarization = True
        tool_context.actions.escalate = True
        return DataPart(data = {"artifact-file-id": file_id})
    return f"Unknown type: {p.type}"
    