class Task:
    def __init__(self, task_type, details, priority=5, deadline=None, max_retries=3):
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.details = details
        self.priority = priority
        self.status = "pending"
        self.children: List[str] = []  # List of child task IDs
        self.feedback = None
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.assigned_to = None
        self.deadline = deadline
        self.attempt_count = 0  # Orchestrator retry count
        self.max_retries = max_retries # Agent retry count
        self.result = None
        self.error = None

    def update_status(self, new_status):
        """Update task status with timestamp."""
        self.status = new_status
        self.updated_at = datetime.now()
        logger.info(f"Task {self.id} status updated to {new_status}")

    def assign_to(self, agent_id):
        """Assign task to an agent."""
        self.assigned_to = agent_id
        self.updated_at = datetime.now()
        logger.info(f"Task {self.id} assigned to agent {agent_id}")

    def add_child(self, child_task_id):
        """Add a child task ID to this task."""
        if child_task_id not in self.children:
            self.children.append(child_task_id)
            self.updated_at = datetime.now()

    def add_feedback(self, feedback_text, rating=None):
        """Add feedback to the task."""
        self.feedback = {
            "text": feedback_text,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        self.updated_at = datetime.now()

    def set_result(self, result):
        """Set the result of the task execution."""
        self.result = result
        self.updated_at = datetime.now()

    def set_error(self, error):
        """Set error information if task fails."""
        self.error = {
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
            "type": error.__class__.__name__
        }
        self.updated_at = datetime.now()

    def can_retry(self):
        """Check if the task can be retried by the agent."""
        return self.attempt_count < self.max_retries

    def increment_attempt(self):
        """Increment the attempt counter."""
        self.attempt_count += 1
        self.updated_at = datetime.now()
        return self.attempt_count

    def is_overdue(self):
        """Check if the task is overdue."""
        if not self.deadline:
            return False
        return datetime.now() > self.deadline

    def to_dict(self):
        """Convert task to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "details": self.details,
            "priority": self.priority,
            "status": self.status,
            "children": self.children.copy(),
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assigned_to": self.assigned_to,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "attempt_count": self.attempt_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data):
        """Create a task from a dictionary."""
        task = cls(
            task_type=data["type"],
            details=data["details"],
            priority=data["priority"]
        )
        task.id = data["id"]
        task.status = data["status"]
        task.children = data["children"].copy()
        task.feedback = data["feedback"]
        task.created_at = datetime.fromisoformat(data["created_at"])
        task.updated_at = datetime.fromisoformat(data["updated_at"])
        task.assigned_to = data["assigned_to"]
        task.deadline = datetime.fromisoformat(data["deadline"]) if data["deadline"] else None
        task.attempt_count = data["attempt_count"]
        task.max_retries = data["max_retries"]
        task.result = data["result"]
        task.error = data["error"]
        return task