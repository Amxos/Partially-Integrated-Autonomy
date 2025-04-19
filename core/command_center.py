# --- Command Center ---

class CommandCenter:
    def __init__(self, agent_registry: AgentRegistry, delegation_tree: DelegationTree, task_orchestrator: TaskOrchestrator):
        self.agent_registry = agent_registry
        self.delegation_tree = delegation_tree
        self.task_orchestrator = task_orchestrator
        self._executor = ThreadPoolExecutor(max_workers=10)  # Adjust as needed
        self._lock = threading.RLock()

    def submit_task(self, task_type: str, details: dict, priority: int = 5, parent_id: str = None, deadline: datetime = None):
        """Submit a new task."""
        try:
            new_task = Task(task_type=task_type, details=details, priority=priority, deadline=deadline)
            self.delegation_tree.add_task(new_task, parent_id)
            self.task_orchestrator.add_task(new_task)
            logger.info(f"Task submitted: {new_task.id} of type {task_type}")
            return new_task.id
        except Exception as e:
            logger.error(f"Failed to submit task: {str(e)}")
            return None
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get the status of a specific task."""
        task = self.delegation_tree.get_task(task_id)
        return task.status if task else None

    def get_task_details(self, task_id: str) -> Optional[dict]:
        """Get details of a specific task."""
        task = self.delegation_tree.get_task(task_id)
        return task.to_dict() if task else None

    def get_agent_status(self, agent_id: str) -> Optional[dict]:
      """Gets the status of a specific agent."""
      agent = self.agent_registry.get_agent(agent_id)
      return agent.get_status() if agent else None

    def list_all_tasks(self) -> List[dict]:
        """List all tasks in the delegation tree."""
        return [task.to_dict() for task in self.delegation_tree.tasks.values()]

    def list_all_agents(self) -> List[dict]:
        """List all agents in the agent registry."""
        return [agent.get_status() for agent in self.agent_registry.get_all_agents().values()]

    def get_task_hierarchy(self, task_id: str) -> Optional[dict]:
        """Get the hierarchical structure of a task and its subtasks."""
        return self.delegation_tree.get_task_hierarchy(task_id)

    def cancel_task(self, task_id: str):
      """Cancels a task and its subtasks. Does *NOT* stop an in-progress task."""
      with self._lock:  # Ensure exclusive access
          task = self.delegation_tree.get_task(task_id)
          if not task:
              logger.warning(f"Attempted to cancel non-existent task {task_id}")
              return False

          if task.status in ("completed", "failed", "cancelled"):
              logger.info(f"Task {task_id} cannot be cancelled (already {task.status}).")
              return False

          #Recursively mark this and all child tasks as cancelled.
          def _cancel_recursive(tid):
            current_task = self.delegation_tree.get_task(tid)
            if current_task: #double check if exists
              current_task.update_status("cancelled")
              for child_id in self.delegation_tree.relationships.get(tid, []): #get all children
                _cancel_recursive(child_id) #recursively cancel children

          _cancel_recursive(task_id)
          logger.info(f"Task {task_id} and all its subtasks have been cancelled.")
          return True

    def save_state(self, filepath: str):
      """Saves the current state of the system (agents, tasks, delegation tree)."""
      try:
        data = {
            "agents": self.agent_registry.to_dict(), #this now uses to_dict() and from_dict()!
            "delegation_tree": self.delegation_tree.to_dict(), #this now uses to_dict() and from_dict()!
        }
        with open(filepath, "wb") as f: #wb for pickle
          pickle.dump(data, f)
        logger.info(f"System state saved to {filepath}")
      except Exception as e:
        logger.error(f"Failed to save system state: {e}")
        raise

    @classmethod
    def load_state(cls, filepath: str, task_orchestrator: TaskOrchestrator):
        """Loads the system state from a file and restarts the orchestrator."""

        try:
            with open(filepath, "rb") as f: #rb for pickle
                data = pickle.load(f)

            # Load delegation tree (it must be loaded *before* agents)
            delegation_tree = DelegationTree.from_dict(data["delegation_tree"])

            # Load AgentRegistry from saved state.
            agent_registry = AgentRegistry() # Create new instance
            agent_registry.load_agents(filepath) #load agents

            # Create CommandCenter
            command_center = cls(agent_registry, delegation_tree, task_orchestrator)

            logger.info(f"System state loaded from {filepath}")
            return command_center

        except FileNotFoundError:
            logger.warning(f"State file not found: {filepath}")
            # Handle missing file - either start fresh or raise error as needed
            raise
        except Exception as e:
            logger.error(f"Failed to load system state: {e}")
            raise
    def shutdown(self):
        """Gracefully shuts down the system."""
        logger.info("System shutdown initiated.")
        self.task_orchestrator.stop()
        self._executor.shutdown(wait=True)
        logger.info("Thread pool executor shut down.")
        logger.info("System shutdown complete.")