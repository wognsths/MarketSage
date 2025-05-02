from typing import Callable
import uuid
from common.types import (
    AgentCard,
    Task,
    TaskSendParams,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    TaskStatus,
    TaskState,
)
from app.common.client.client import A2AClient

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """
    A class that manages the connection to a remote agent.

    This class is responsible for sending tasks to the remote agent, handling streaming
    and non-streaming responses, and invoking optional callbacks to notify the system
    of task updates or results.
    """

    def __init__(self, agent_card: AgentCard):
        """
        Initialize the remote agent connection using its agent card.

        Args:
            agent_card (AgentCard): The metadata and connection info of the remote agent.
        """
        self.agent_client = A2AClient(agent_card)
        self.card = agent_card
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        """
        Return the agent card associated with this connection.

        Returns:
            AgentCard: The agent's metadata.
        """
        return self.card

    async def send_task(
        self,
        request: TaskSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | None:
        """
        Send a task to the remote agent and handle the response.

        If the agent supports streaming, this will process incoming streaming updates
        until a final result is received. Otherwise, it will await a single non-streaming response.

        Args:
            request (TaskSendParams): The task request payload.
            task_callback (TaskUpdateCallback, optional): A function to call on each task update.

        Returns:
            Task | None: The final task result, if available.
        """
        if self.card.capabilities.streaming:
            task = None
            if task_callback:
                # Notify that the task has been submitted
                task_callback(Task(
                    id=request.id,
                    sessionId=request.sessionId,
                    status=TaskStatus(
                        state=TaskState.SUBMITTED,
                        message=request.message,
                    ),
                    history=[request.message],
                ), self.card)

            async for response in self.agent_client.send_task_streaming(request.model_dump()):
                merge_metadata(response.result, request)

                # Ensure metadata propagation and assign unique message ID
                if (hasattr(response.result, 'status') and
                    hasattr(response.result.status, 'message') and
                    response.result.status.message):
                    merge_metadata(response.result.status.message, request.message)
                    m = response.result.status.message
                    if not m.metadata:
                        m.metadata = {}
                    if 'message_id' in m.metadata:
                        m.metadata['last_message_id'] = m.metadata['message_id']
                    m.metadata['message_id'] = str(uuid.uuid4())

                if task_callback:
                    task = task_callback(response.result, self.card)

                if hasattr(response.result, 'final') and response.result.final:
                    break

            return task

        else:  # Non-streaming case
            response = await self.agent_client.send_task(request.model_dump())
            merge_metadata(response.result, request)

            # Metadata propagation and message ID handling
            if (hasattr(response.result, 'status') and
                hasattr(response.result.status, 'message') and
                response.result.status.message):
                merge_metadata(response.result.status.message, request.message)
                m = response.result.status.message
                if not m.metadata:
                    m.metadata = {}
                if 'message_id' in m.metadata:
                    m.metadata['last_message_id'] = m.metadata['message_id']
                m.metadata['message_id'] = str(uuid.uuid4())

            if task_callback:
                task_callback(response.result, self.card)

            return response.result


def merge_metadata(target, source):
    """
    Merge metadata from the source object into the target object.

    This is used to preserve and propagate context (e.g., conversation_id, user_id)
    from the original request message to the task response or status update.

    Args:
        target: The object receiving metadata (e.g., TaskStatus.message).
        source: The object providing metadata (e.g., TaskSendParams.message).
    """
    if not hasattr(target, 'metadata') or not hasattr(source, 'metadata'):
        return
    if target.metadata and source.metadata:
        target.metadata.update(source.metadata)
    elif source.metadata:
        target.metadata = dict(**source.metadata)
