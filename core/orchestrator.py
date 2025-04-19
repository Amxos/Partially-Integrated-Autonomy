class TaskOrchestrator:
    def __init__(self, agent_registry: AgentRegistry, retry_delay: int = 5, max_orchestrator_retries: int = 3):
        self.task_queue = PriorityQueue()
        self.agent_registry = agent_registry
        self._stop_event = threading.Event()
        self.retry_delay = retry_delay
        self.max_orchestrator_retries = max_orchestrator_retries

    def add_task(self, task: Task):
        """Adds a task to the orchestration queue."""
        self.task_queue.put((task.priority, task))
        logger.info(f"Task {task.id} added to orchestration queue with priority {task.priority}.")

    def _assign_task(self):
        """Assigns the highest priority task to a suitable agent."""
        if self.task_queue.empty():
            return

        priority, task = self.task_queue.get()

        if task.is_overdue():
            task.update_status("failed_deadline")
            logger.warning(f"Task {task.id} missed deadline.")
            return

        best_agent = None
        best_score = -float('inf')  # Initialize with negative infinity

        for agent in self.agent_registry.get_all_agents().values():
            # Skill Matching (Slightly Enhanced)
            skill_match = False
            for agent_skill in agent.skills:
                if isinstance(agent_skill, str) and task.type == agent_skill:
                    skill_match = True
                    break  # Exact match
                elif hasattr(agent_skill, 'name') and task.type == agent_skill.name:
                    skill_match = True
                    break # Match with skill object
            if not skill_match:
                continue  # Skip if no skill match


            # Agent Capacity and Workload
            if agent.workload >= getattr(agent, 'capacity', 10):  # Default capacity of 10 if not defined
                continue  # Skip if agent at or above capacity

            # Agent Health
            health_score = agent.health_history.get_ewma()  # Use EWMA for health

            # Calculate Suitability Score
            #  - Prioritize health.
            #  - Then consider workload (lower is better).  Normalize workload by capacity.
            #  - Add a small bonus for higher access level (if relevant).
            suitability_score = (
                health_score * 10  # Weight health significantly
                - (agent.workload / getattr(agent, 'capacity', 10))  # Normalized workload
                + agent.access_level * 0.1  # Small bonus for access level
            )

            if suitability_score > best_score:
                best_score = suitability_score
                best_agent = agent

        # ... (Rest of the _assign_task method - task assignment and re-queuing logic - remains the same)
        if best_agent:
            if best_agent.receive_task(task):
                logger.info(f"Task {task.id} assigned to agent {best_agent.id}.")
            else:
                logger.warning(f"Failed to assign task {task.id} to agent {best_agent.id}. Re-queueing...")
                # Re-add to queue with slightly reduced priority, and increment orchestrator retry count
                task.priority = max(1, task.priority -1) #reduce priority.
                task.attempt_count += 1 # increment orchestrator retries

                if task.attempt_count > self.max_orchestrator_retries:
                  logger.error(f"Task {task.id} exceeded max orchestrator retries. Moving to dead letter queue (not implemented).")
                  task.update_status("failed") #setting status, to failed since no dead letter queue
                else:
                  self.add_task(task) # Re-add the task.

        else:
            # No agent found, re-queue
            logger.warning(f"No suitable agent found for task {task.id}. Re-queueing...")
            task.priority = max(1, task.priority -1) #reduce priority.
            task.attempt_count += 1

            if task.attempt_count > self.max_orchestrator_retries:
              logger.error(f"Task {task.id} exceeded max orchestrator retries. Moving to dead letter queue (not implemented).")
              task.update_status("failed") #setting status, to failed since no dead letter queue.
            else:
              time.sleep(self.retry_delay)
              self.add_task(task)

    def run(self):
        """Runs the task orchestration loop."""
        logger.info("Task Orchestrator started.")
        while not self._stop_event.is_set():
            self._assign_task()
            time.sleep(1)
        logger.info("Task Orchestrator stopped.")

    def stop(self):
        """Stops the task orchestration loop."""
        self._stop_event.set()
        logger.info("Task Orchestrator stop signal received.")