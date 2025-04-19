# This file contains the BaseAgent class, which is the parent class for all agents in the system. It provides basic functionality for task processing, management, and communication with other agents. The BaseAgent class is designed
# to be subclassed by specific agent types, such as TaskAgent or ChatAgent, which implement the logic for handling different types of tasks or interactions.

#Python Libraries
import uuid
import threading
from datetime import datetime
from collections import deque
from queue import PriorityQueue
from typing import Optional ,  Dict,  List, Any # Import the necessary modules


#Internal Libraries
from core.exceptions import  AccessDeniedError, NotImplementedError  
from agents.Health import HealthHistory
from utils.logger import setup_logger
import logging

logger = setup_logger(__name__) # Create a logger for the agent module



class BaseAgent:
    def __init__(self, role: str, skills: List[str], access_level: int = 1):
        self.id = str(uuid.uuid4())
        self.role = role
        self.skills = skills
        self.audit_log: List[Dict] = []
        self.workload = 0
        self.communication_channel: Dict[str, Any] = {}
        self.priority_queue = PriorityQueue()
        self.access_level = access_level
        self._lock = threading.RLock()  # Thread-safe operations
        self.created_at = datetime.now()
        self.last_active = self.created_at
        self.status = "ready"
        self.error_count = 0
        self.health_history = HealthHistory()
        logger.info(f"Agent {self.id} ({role}) initialized with skills: {skills}")

        


    def receive_task(self, task):
        """Receive a task for processing."""
        with self._lock:
            try:
                task.assigned_to = self.id # Directly assign
                self.priority_queue.put((-task.priority, task))  # Use put() for PriorityQueue
                self.log_activity("TASK_RECEIVED", task.id)
                self.workload += 1
                self.last_active = datetime.now()
                logger.info(f"Agent {self.id} ({self.role}) received task {task.id} with priority {task.priority}")
                return True
            except Exception as e:
                logger.error(f"Error receiving task for agent {self.id}: {e}", exc_info=True)
                return False

    def process_task(self):
        """Process the highest priority task in the queue."""
        with self._lock:
            if self.priority_queue.empty():
                return None

            try:
                _, task = self.priority_queue.get()  # Use get() for PriorityQueue
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
                    logger.error(f"Agent {self.id} failed to execute task {task.id}: {e}", exc_info=True)
                    task.set_error(e)

                    if task.can_retry():
                        task.update_status("retry_pending")
                        logger.info(f"Task {task.id} will be retried. Attempt {task.attempt_count}/{task.max_retries}")
                        new_priority = max(1, task.priority - 1)
                        self.priority_queue.put((-new_priority, task)) # Use put
                        self.workload += 1
                    else:
                        task.update_status("failed")
                        logger.warning(f"Task {task.id} has failed permanently after {task.attempt_count} attempts")

                    self.log_activity("TASK_FAILED", task.id, str(e))
                    return None

            except Exception as e:
                logger.error(f"Error processing task queue for agent {self.id}: {e}", exc_info=True)
                self.error_count += 1
                return None


    def _execute_task(self, task):
        """Execute a task (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _execute_task")

    def log_activity(self, event: str, task_id: str, details: Optional[str] = None):
        """Log an activity event."""
        with self._lock:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.id,
                "agent_role": self.role,
                "event": event,
                "task_id": task_id,
                "details": details,
            }
            self.audit_log.append(log_entry)
            logger.info(log_entry) #log


    def communicate_result(self, task, result):
        """Communicate the result of a task to child agents."""
        if not task.children:
            return

        # Assuming you have a way to get agents by ID (e.g., through the AgentRegistry)
        from ..core.registry import AgentRegistry  # Import here to avoid circular dependency

        for child_id in task.children:
            try:
                child_agent = AgentRegistry.get_agent(child_id)
                if child_agent:
                    child_agent.receive_message(self.id, {"task_id": task.id, "result": result})
            except Exception as e:
                logger.error(f"Error communicating result to agent {child_id}: {e}", exc_info=True)

    def receive_message(self, sender_id: str, message: Dict):
        """Receive a message from another agent."""
        try:
            # Assuming you have a way to get agents by ID
            from ..core.registry import AgentRegistry  # Import here to avoid circular dependency
            sender = AgentRegistry.get_agent(sender_id)
            if not sender:
                logger.warning(f"Message received from unknown agent {sender_id}")
                return False

            if sender.access_level < self.access_level:
                logger.warning(
                    f"Access denied: Agent {sender_id} (level {sender.access_level}) "
                    f"tried to communicate with {self.id} (level {self.access_level})"
                )
                self.log_activity("ACCESS_DENIED", None, f"From: {sender_id}, Message: {message}")
                raise AccessDeniedError(f"Agent {sender_id} has insufficient access level")

            with self._lock:
                self.communication_channel[sender_id] = message
                self.log_activity("MESSAGE_RECEIVED", message.get("task_id"), f"From: {sender_id}")
                self.last_active = datetime.now()
            return True

        except Exception as e:
            logger.error(f"Error receiving message from {sender_id}: {e}", exc_info=True)
            return False

    def get_status(self) -> Dict:
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
                "uptime": (datetime.now() - self.created_at).total_seconds(),
            }

    

    def reset(self):
        """Reset the agent to its initial state."""
        with self._lock:
            try:
                self.audit_log = []
                self.communication_channel = {}
                self.priority_queue = PriorityQueue()  # Use put() and get()
                self.workload = 0
                self.status = "ready"
                self.error_count = 0
                self.last_active = datetime.now()
                logger.info(f"Agent {self.id} ({self.role}) has been reset")
                return True
            except Exception as e:
                logger.error(f"Error resetting agent {self.id}: {e}", exc_info=True)
                return False

    def to_dict(self):
      """Serialize the agent's state to a dictionary."""
      with self._lock:
          priority_queue_contents = [(-priority, task.to_dict()) for priority, task in self.priority_queue.queue] #Use Task.to_dict()

          return {
              "id": self.id,
              "role": self.role,
              "skills": self.skills,
              "audit_log": self.audit_log,
              "workload": self.workload,
              "communication_channel": self.communication_channel,
              "access_level": self.access_level,
              "created_at": self.created_at.isoformat(),
              "last_active": self.last_active.isoformat(),
              "status": self.status,
              "error_count": self.error_count,
              "priority_queue_contents": priority_queue_contents,
              "health_history": [h for h in self.health_history.health_scores]
          }

    @classmethod
    def from_dict(cls, data: Dict) -> "BaseAgent":
      """Deserialize an agent's state from a dictionary."""
      agent = cls(role=data["role"], skills=data["skills"], access_level=data["access_level"])
      with agent._lock:
          agent.id = data["id"]
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
              from ..core.task import Task  # Import here to avoid circular dependency
              task = Task.from_dict(task_data)
              agent.priority_queue.put((priority, task))  # Use put()

          #Restore health
          agent.health_history = HealthHistory()
          agent.health_history.health_scores = deque(data["health_history"], maxlen = agent.health_history.health_scores.maxlen)
      return agent