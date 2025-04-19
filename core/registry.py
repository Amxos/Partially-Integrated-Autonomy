# This file contains the AgentRegistry class, which is a singleton class that manages the registration and retrieval of agents in the simulation.
# The AgentRegistry class provides methods to register, unregister, retrieve, and reset agents. It also provides methods to save and load agents to and from a file.

# Python Libraries
import logging
import threading
import pickle
from typing import Dict, List, Optional, Type as Type




# PIA Libraries
from agents.BaseAgent import BaseAgent
from core.exceptions import ValueError
from utils.logger import setup_logger

logger = setup_logger(__name__)




class AgentRegistry:
    _instance = None
    _lock = threading.Lock()
    pass
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgentRegistry, cls).__new__(cls)
                cls._instance.agents = {}
                cls._instance._agent_lock = threading.RLock()
            return cls._instance

    @classmethod
    def register(cls, agent: BaseAgent):
        """Registers an agent with the registry."""
        with cls._instance._agent_lock:
            if agent.id in cls._instance.agents:
                raise ValueError(f"Agent with ID {agent.id} already registered.")
            cls._instance.agents[agent.id] = agent
            logger.info(f"Agent {agent.id} ({agent.role}) registered.")

    @classmethod
    def unregister(cls, agent_id: str):
        """Unregisters an agent from the registry."""
        with cls._instance._agent_lock:
            if agent_id not in cls._instance.agents:
                raise ValueError(f"Agent with ID {agent_id} not found.")
            del cls._instance.agents[agent_id]
            logger.info(f"Agent {agent_id} unregistered.")

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        """Retrieves an agent by its ID."""
        with cls._instance._agent_lock:
            return cls._instance.agents.get(agent_id)

    @classmethod
    def get_all_agents(cls) -> Dict[str, BaseAgent]:
        """Returns a dictionary of all registered agents."""
        with cls._instance._agent_lock:
            return cls._instance.agents.copy()

    @classmethod
    def get_agents_by_role(cls, role: str) -> List[BaseAgent]:
        """Returns a list of agents with the specified role."""
        with cls._instance._agent_lock:
            return [agent for agent in cls._instance.agents.values() if agent.role == role]

    @classmethod
    def get_agents_by_skill(cls, skill: str) -> List[BaseAgent]:
        """Returns a list of agents with the specified skill."""
        with cls._instance._agent_lock:
            return [agent for agent in cls._instance.agents.values() if skill in agent.skills]

    @classmethod
    def reset_all_agents(cls):
        """Resets all registered agents."""
        with cls._instance._agent_lock:
            for agent in cls._instance.agents.values():
                agent.reset()
            logger.info("All agents have been reset.")

    @classmethod
    def save_agents(cls, filepath: str):
      with cls._instance._agent_lock:
        agent_data = {agent_id: agent.to_dict() for agent_id, agent in cls._instance.agents.items()}

        try:
            with open(filepath, 'wb') as f:  # Use 'wb' for pickle
                pickle.dump(agent_data, f)
            logger.info(f"Agents saved to {filepath}")

        except Exception as e:
          logger.error(f"Error saving agents to file: {e}")
          raise

    @classmethod
    def load_agents(cls, filepath: str):
        with cls._instance._agent_lock:
            try:
                with open(filepath, 'rb') as f:  # Use 'rb' for pickle
                    agent_data = pickle.load(f)

                # Clear the current agent registry
                cls._instance.agents.clear()

                # Load agents and re-register, ensuring AgentRegistry consistency
                for agent_id, agent_dict in agent_data.items():
                    agent = BaseAgent.from_dict(agent_dict) # Use the from_dict for agent.
                    cls._instance.agents[agent_id] = agent  # Directly add to the dictionary
                    logger.info(f"Agent {agent.id} ({agent.role}) loaded and re-registered.")

                logger.info(f"Agents loaded from {filepath}")

            except FileNotFoundError:
                logger.warning(f"Agent file not found: {filepath}")
                # Optionally initialize a new AgentRegistry if the file doesn't exist
                cls._instance.agents = {}

            except Exception as e:
                logger.error(f"Error loading agents: {e}")
                raise

    def to_dict(self):
        """Serializes the agent registry to a dictionary."""
        with self._agent_lock:
            return {agent_id: agent.to_dict() for agent_id, agent in self.agents.items()}