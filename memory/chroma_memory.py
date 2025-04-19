# This is the ChromaMemory class that extends the BaseAgent class and adds ChromaDB integration for memory management.

# External Libraries
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils import embedding_functions as EmbeddingFunction


# Standard Library
import uuid
from datetime import datetime
'import logging'
import json
import heapq 
from typing import Any, List, Optional 
from collections import deque
from queue import PriorityQueue

# Internal Libraries
from my_projectPIA.core.registry import registry as AgentRegistry
from my_projectPIA.core.task import Task  
from my_projectPIA.utils.logger import setup_logger  
from my_projectPIA.core.exceptions import AccessDeniedError  
from my_projectPIA.agents.Health import HealthHistory

logger = setup_logger(__name__)  # Create a logger



class ChromaMemory:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memory_store = {}

    def add_memory(self, key: str, value: Any):
        self.memory_store[key] = value

    def get_memory(self, key: str) -> Optional[Any]:
        return self.memory_store.get(key)

    def delete_memory(self, key: str):
        if key in self.memory_store:
            del self.memory_store[key]

        try:
            # Initialize ChromaDB client (in-memory for now - for simplicity)
            self.chroma_client = chromadb.Client()

            # Choose a collection name (agent ID is unique, so good choice)
            collection_name = f"agent_memory_{self.id}"

            # Create or get the collection
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                embedding_function=EmbeddingFunction.SentenceTransformerEmbeddingFunction() # Using SentenceTransformers
            )
            logger.info(f"ChromaDB collection '{collection_name}' initialized for agent {self.id}")

        except Exception as e:
            logger.error(f"Error initializing ChromaDB for agent {self.id}: {e}", exc_info=True)
            self.chroma_client = None  # Handle error - set client to None
            self.chroma_collection = None

    def receive_task(self, task):
        """Receive a task for processing."""
        with self._lock:
            try:
                task.assign_to(self.id)
                heapq.heappush(self.priority_queue.queue, (-task.priority, task))
                self.log_activity("TASK_RECEIVED", task.id)
                self.workload += 1
                self.last_active = datetime.now()
                logger.info(f"Agent {self.id} ({self.role}) received task {task.id} with priority {task.priority}")
                return True
            except Exception as e:
                logger.error(f"Error receiving task for agent {self.id}: {str(e)}")
                return False

    def process_task(self):
        """Process the highest priority task in the queue."""
        with self._lock:
            if self.priority_queue.empty():
                return None

            try:
                _, task = heapq.heappop(self.priority_queue.queue)
                self.workload = max(0, self.workload - 1)

                task.update_status("in_progress")
                task.increment_attempt()

                try:
                    logger.info(f"Agent {self.id} ({self.role}) executing task {task.id}")
                    result = self._execute_task(task)
                    task.set_result(result)
                    task.update_status("completed")
                    self.log_activity("TASK_COMPLETED", task.id)
                    self.communicate_result(task, result)
                    self.last_active = datetime.now()
                    return result
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Agent {self.id} failed to execute task {task.id}: {str(e)}", exc_info=True)
                    task.set_error(e)

                    if task.can_retry():
                        task.update_status("retry_pending")
                        logger.info(f"Task {task.id} will be retried. Attempt {task.attempt_count}/{task.max_retries}")
                        new_priority = max(1, task.priority - 1)
                        heapq.heappush(self.priority_queue.queue, (-new_priority, task))
                        self.workload += 1
                    else:
                        task.update_status("failed")
                        logger.warning(f"Task {task.id} has failed permanently after {task.attempt_count} attempts")

                    self.log_activity("TASK_FAILED", task.id, str(e))
                    return None
            except Exception as e:
                logger.error(f"Error processing task queue for agent {self.id}: {str(e)}", exc_info=True)
                self.error_count += 1
                return None

    def _execute_task(self, task):
        """Execute a task (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _execute_task")

    def log_activity(self, event, task_id, details=None):
        """Log an activity event."""
        with self._lock:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.id,
                "agent_role": self.role,
                "event": event,
                "task_id": task_id,
                "details": details
            }
            self.audit_log.append(log_entry)
            log_message = json.dumps(log_entry)  # Log as JSON
            logger.info(log_message)


    def communicate_result(self, task, result):
        """Communicate the result of a task to child agents."""
        if not task.children:
            return

        for child_id in task.children:
            try:
                child_agent = AgentRegistry.get_agent(child_id)
                if child_agent:
                    child_agent.receive_message(self.id, {"task_id": task.id, "result": result})
            except Exception as e:
                logger.error(f"Error communicating result to agent {child_id}: {str(e)}")

    def receive_message(self, sender_id, message):
        """Receive a message from another agent."""
        try:
            sender = AgentRegistry.get_agent(sender_id)
            if not sender:
                logger.warning(f"Message received from unknown agent {sender_id}")
                return False

            if sender.access_level < self.access_level:
                logger.warning(f"Access denied: Agent {sender_id} (level {sender.access_level}) " +
                              f"tried to communicate with {self.id} (level {self.access_level})")
                self.log_activity("ACCESS_DENIED", None, f"From: {sender_id}, Message: {message}")
                raise AccessDeniedError(f"Agent {sender_id} has insufficient access level")

            with self._lock:
                self.communication_channel[sender_id] = message
                self.log_activity("MESSAGE_RECEIVED", message.get("task_id"), f"From: {sender_id}")
                self.last_active = datetime.now()

            return True
        except Exception as e:
            logger.error(f"Error receiving message from {sender_id}: {str(e)}")
            return False

    def get_status(self):
        """Get the current status of the agent."""
        with self._lock:
            return {
                "id": self.id,
                "role": self.role,
                "status": self.status,
                "workload": self.workload,
                "queue_size": self.priority_queue.qsize(),
                "error_count": self.error_count,
                "last_active": self.last_active.isoformat(),
                "uptime": (datetime.now() - self.created_at).total_seconds()
            }

    def clear_memory(self, older_than=None):
        """Clear agent's memory, optionally only items older than a specific time."""
        with self._lock:
            if not older_than:
                self.memory.clear()
                logger.info(f"Memory cleared for agent {self.id}")
                return True

            to_keep = deque(maxlen=self.memory.maxlen)
            for item in self.memory:
                if "timestamp" in item and datetime.fromisoformat(item["timestamp"]) >= older_than:
                    to_keep.append(item)

            self.memory = to_keep
            logger.info(f"Memory cleared for agent {self.id} (items older than {older_than})")
            return True

    def add_to_memory(self, data):
        """Add an item to the agent's memory and ChromaDB."""
        with self._lock:
            if isinstance(data, dict) and "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()

            self.memory.append(data) # Still keep it in deque

            # --- ChromaDB Integration: Add to Vector DB ---
            if self.chroma_collection and isinstance(data, str): # Only add string data for now (can expand)
                try:
                    self.chroma_collection.add(
                        documents=[data], # Data as document
                        ids=[str(uuid.uuid4())], # Generate unique ID for each memory entry
                        metadatas=[{"agent_id": self.id, "timestamp": data.get("timestamp", datetime.now().isoformat()) if isinstance(data, dict) else datetime.now().isoformat()}] # Add metadata
                    )
                    logger.debug(f"Added data to ChromaDB collection for agent {self.id}: {data[:50]}...") # Log, truncate long data
                except Exception as e:
                    logger.error(f"Error adding data to ChromaDB for agent {self.id}: {e}", exc_info=True)
            return True

    def query_memory(self, query_text: str, n_results: int = 5) -> List[str]:
        """Query ChromaDB memory for relevant information."""
        if not self.chroma_collection:
            logger.warning(f"ChromaDB not initialized for agent {self.id}. Memory query disabled.")
            return []  # Return empty list if ChromaDB not available

        try:
            results = self.chroma_collection.query(
                query_texts=[query_text], # Query text
                n_results=n_results # Number of results to return
            )
            retrieved_documents = results.get("documents", [[]])[0] # Extract documents from results
            logger.debug(f"Memory query for agent {self.id}: '{query_text[:50]}...', retrieved {len(retrieved_documents)} results.") # Log query and results
            return retrieved_documents # Return the list of retrieved documents (strings)
        except Exception as e:
            logger.error(f"Error querying ChromaDB memory for agent {self.id}: {e}", exc_info=True)
            return [] # Return empty list on error

    def reset(self):
        """Reset the agent to its initial state."""
        with self._lock:
            try:
                self.memory.clear()
                self.audit_log = []
                self.communication_channel = {}
                self.priority_queue = PriorityQueue()
                self.workload = 0
                self.status = "ready"
                self.error_count = 0
                self.last_active = datetime.now()
                logger.info(f"Agent {self.id} ({self.role}) has been reset")
                return True
            except Exception as e:
                logger.error(f"Error resetting agent {self.id}: {str(e)}")
                return False

    def to_dict(self):
        """Serialize the agent's state to a dictionary."""
        with self._lock:
            priority_queue_contents = [(-priority, task.to_dict()) for priority, task in self.priority_queue.queue]

            return {
                "id": self.id,
                "role": self.role,
                "skills": self.skills,
                "memory": list(self.memory),  # Convert deque to list
                "audit_log": self.audit_log,
                "workload": self.workload,
                "communication_channel": self.communication_channel,
                "access_level": self.access_level,
                "created_at": self.created_at.isoformat(),
                "last_active": self.last_active.isoformat(),
                "status": self.status,
                "error_count": self.error_count,
                "priority_queue_contents": priority_queue_contents,
                "health_history": [h for h in self.health_history.health_scores] #added health history
            }

    @classmethod
    def from_dict(cls, data):
      """Deserialize an agent's state from a dictionary."""
      agent = cls(role=data["role"], skills=data["skills"], access_level=data["access_level"])
      with agent._lock:
          agent.id = data["id"]
          agent.memory = deque(data["memory"], maxlen=100)  # Restore deque
          agent.audit_log = data["audit_log"]
          agent.workload = data["workload"]
          agent.communication_channel = data["communication_channel"]
          agent.created_at = datetime.fromisoformat(data["created_at"])
          agent.last_active = datetime.fromisoformat(data["last_active"])
          agent.status = data["status"]
          agent.error_count = data["error_count"]

          # Restore the priority queue content, creating Task objects.
          agent.priority_queue = PriorityQueue()
          for priority, task_data in data["priority_queue_contents"]:
              task = Task.from_dict(task_data)  # Use Task.from_dict
              heapq.heappush(agent.priority_queue.queue, (priority, task))

          #Restore health
          agent.health_history = HealthHistory()
          agent.health_history.health_scores = deque(data["health_history"], maxlen = agent.health_history.health_scores.maxlen )

      return ChromaMemory
    
