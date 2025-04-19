class DelegationTree:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.relationships: Dict[str, List[str]] = {}  # Parent -> Children
        self._lock = threading.RLock()  # Thread-safe operations

    def add_task(self, task, parent_id=None):
        """Add a task to the delegation tree."""
        with self._lock:
            self.tasks[task.id] = task
            if parent_id:
                if parent_id not in self.tasks:
                    raise DataIntegrityError(f"Parent task {parent_id} not found")

                self.tasks[parent_id].add_child(task.id)

                # Initialize the parent's children list in relationships if not exists
                if parent_id not in self.relationships:
                    self.relationships[parent_id] = []

                # Add this task as a child to the parent
                self.relationships[parent_id].append(task.id)

            # Initialize this task's children list
            self.relationships[task.id] = []

            logger.info(f"Task {task.id} added to delegation tree" +
                      (f" with parent {parent_id}" if parent_id else ""))
            return task.id

    def get_task(self, task_id) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found in delegation tree")
                return None
            return self.tasks[task_id]

    def get_children(self, task_id) -> List[Task]:
        """Get all children of a task."""
        with self._lock:
            if task_id not in self.relationships:
                logger.warning(f"Task {task_id} has no relationships")
                return []
            return [self.tasks[child_id] for child_id in self.relationships[task_id]
                    if child_id in self.tasks]

    def update_task_status(self, task_id, new_status):
        """Update a task's status."""
        with self._lock:
            if task_id not in self.tasks:
                raise DataIntegrityError(f"Task {task_id} not found")

            self.tasks[task_id].update_status(new_status)
            return True

    def get_task_hierarchy(self, task_id) -> Optional[Dict]:
        """Get the complete hierarchy of a task (tree view)."""
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found in delegation tree")
                return None

            def build_hierarchy(tid):
                task = self.tasks[tid]
                children = []
                for child_id in self.relationships.get(tid, []):
                    if child_id in self.tasks:
                        children.append(build_hierarchy(child_id))

                return {
                    "id": task.id,
                    "type": task.type,
                    "status": task.status,
                    "children": children
                }

            return build_hierarchy(task_id)

    def remove_task(self, task_id):
        """Remove a task and all its children from the delegation tree."""
        with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found in delegation tree")
                return False

            # Remove all children recursively
            for child_id in self.relationships.get(task_id, []).copy():
                self.remove_task(child_id)

            # Remove from all parent relationships
            for parent_id, children in self.relationships.items():
                if task_id in children:
                    self.relationships[parent_id].remove(task_id)

            # Remove the task's own relationships and the task itself
            if task_id in self.relationships:
                del self.relationships[task_id]

            del self.tasks[task_id]
            logger.info(f"Task {task_id} removed from delegation tree")
            return True

    def to_dict(self) -> Dict:
        """Serialize the entire DelegationTree to a dictionary."""
        with self._lock:
            tasks_data = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
            return {
                "tasks": tasks_data,
                "relationships": self.relationships.copy()
            }
    @classmethod
    def from_dict(cls, data):
      """Deserialize a DelegationTree from a dictionary."""
      tree = cls()
      with tree._lock:
          # First, create all Task objects without relationships
          for task_id, task_data in data["tasks"].items():
              tree.tasks[task_id] = Task.from_dict(task_data)

          # Then, restore the relationships
          tree.relationships = data["relationships"].copy()

          # Validate relationships:
          for parent_id, children_ids in tree.relationships.items():
              if parent_id not in tree.tasks:
                  raise DataIntegrityError(f"Parent task ID {parent_id} in relationships not found in tasks.")
              for child_id in children_ids:
                  if child_id not in tree.tasks:
                      raise DataIntegrityError(f"child task ID {child_id} in relationships not found in tasks.")

      return tree