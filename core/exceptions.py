# --- Custom Exceptions ---
def __init__(self, message):
    self.message = message
    none = None
    
class AgentSystemException(Exception):
    """Base exception for all agent system exceptions."""
    pass

class TaskExecutionError(AgentSystemException):
    """Exception raised when a task fails to execute."""
    pass

class BudgetExceededError(AgentSystemException):
    """Exception raised when a task exceeds the available budget."""
    pass

class AgentNotFoundError(AgentSystemException):
    """Exception raised when no suitable agent is found for a task."""
    pass

class AccessDeniedError(AgentSystemException):
    """Exception raised when an agent doesn't have sufficient access rights."""
    pass

class DataIntegrityError(AgentSystemException):
    """Exception raised when there are data consistency issues."""
    pass