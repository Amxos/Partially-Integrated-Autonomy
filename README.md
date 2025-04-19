
```markdown
# Partially Integrated Autonomy (P.I.A)

## Overview

PIA (Partially Integrated Autonomy) is an agent framework designed for building sophisticated AI systems. Version 0.5 represents a strategic move towards a **modular foundation** to enable future growth and better integration of modern AI. The core goal is to create robust and flexible autonomous systems capable of handling complex tasks. This version prioritizes **horizontal flexibility** through modularity over the "**vertical depth** (specialized agents)" present in earlier iterations.

## Key Features 

*   **Task-Centric Design**: Features **hierarchical task management** via `DelegationTree`, supporting **parent-child dependencies**, **priority queues**, **deadlines**, **retries**, and **explicit task lifecycle management**. It also includes **built-in error handling** (e.g., `BudgetExceededError`, retry logic at both agent and orchestrator levels).
*   **Decoupled Memory Management**: Introduction of a dedicated **Memory Agent** to centralize memory operations (storage, retrieval, caching), eliminating redundant memory logic in individual agents. Agents requiring memory now depend on the Memory Agent, simplifying their code and reducing tight coupling. The system currently uses **ChromaDB for vector embeddings and memory**, but is designed with **pluggable memory** capabilities, allowing for swapping memory backends (e.g., ChromaDB to Pinecone).
*   **Modular AI Agents**: Includes specialized agents for LLM interactions such as **`OpenAIAgent` and `GeminiAgent`**. These agents offer **clean interfaces for future agents** and standardized interfaces for model-agnostic task execution, allowing for **plug-and-play design** and easy swapping of LLM providers (OpenAI ↔ Gemini).
*   **Specialized Agents**: Agents such as the WebResearcherAgent, CEOAgent, and the ones listed above make this a modular, robust framework for workflows and automating complex tasks.
*   **Advanced Task Orchestration and Delegation Tree**: Improved mechanisms for managing and delegating tasks through the `DelegationTree`.
*   **Cost Efficiency**: Centralized memory via the `MemoryAgent` reduces redundant API calls (e.g., cached LLM responses reused across agents).
*   **Extensibility**: Clear patterns for adding new agents (e.g., `WebResearcher`) or memory backends.

## Architecture (v0.5)

The v0.5 architecture emphasizes **modularity** and decoupled components. Key components include:

*   **Task Orchestrator**: Responsible for managing the execution of tasks.
*   **DelegationTree**: A hierarchical structure for organizing and managing tasks with parent-child dependencies.
*   **Memory Agent**: A dedicated agent that handles memory storage, retrieval, and caching for other agents.
*   **LLM Agents**: Agents like `OpenAIAgent` and `GeminiAgent` provide standardized interfaces for interacting with their respective language models.
*   **Base Agent**: A fundamental class providing core functionalities like logging, memory interaction (using ChromaDB by default), and task handling.
*   **Agent Registry**: Manages the lifecycle and accessibility of agents within the system.

## Comparison to Autogen

PIA v0.5 is quite advanced, even compared to well known frameworks. Distinct differences compared to AutoGen:

| **Aspect**            | **PIA Framework (v0.5)**                      | **Autogen**                             |
| :-------------------- | :-------------------------------------------- | :-------------------------------------- |
| **Primary Focus**     | Task orchestration, workflows, reliability    | Conversational agents, LLM-driven automation |
| **Task Management**   | Explicit hierarchies, deadlines, priorities   | Implicit via agent conversations        |
| **Agent Communication** | Result passing via parent-child tasks        | Direct chat-based interactions          |
| **Memory**            | ChromaDB + deque for structured data         | LLM context windows or external databases |
| **Concurrency**       | Thread-based                                 | Async-first (e.g., `asyncio`)           |
| **Use Case Fit**      | Complex workflows (e.g., data pipelines)     | Collaborative problem-solving (e.g., coding) |
| **Learning Curve**    | Moderate (requires OOP/threading knowledge)  | Lower (declarative agent definitions)    |
| **Integration**       | Customizable (e.g., ChromaDB, web scraping) | Tight LLM integration (e.g., GPT-4)     |

## Getting Started

To begin using PIA :

*   Clone the repo
*   Set up environment variables, such as the `OPENAI_API_KEY`. This can be done via a `.env` file.
*   The framework utilizes logging for tracking activities and potential issues.
*   Dependencies need to be installed, these are ChromaDB, python libraries such as threading, logging, etc. y

## Key Concepts (v0.5)

*   **DelegationTree**: A hierarchical structure for managing and organizing tasks with parent-child dependencies.
*   **AgentRegistry**: A central component responsible for managing the creation, retrieval, and lifecycle of agents within the system.
*   **BaseAgent**: The fundamental building block for all agents, providing core functionalities like task handling, memory interaction (using ChromaDB by default), and communication.
*   **Task**: A unit of work with a defined lifecycle, including status updates, assignment to agents, and the recording of results or errors.
*   **Memory Agent**: A specialized agent dedicated to managing the memory of other agents.

## Areas for Further Development

*   **Dynamic Dependency Injection**: Automate dependency resolution (e.g., via a service locator or DI container).
*   **Distributed Memory Agent**: Support Redis/Elasticsearch for large-scale, low-latency memory.
*   **Autogen Integration**: Bridge PIA’s task-centric agents with Autogen’s conversational agents for hybrid workflows (e.g., Autogen plans → PIA executes).
*   **MCP & A2A Integration**: These recently released protocols stand as new significant advancements in the Agent sector, and implementing them would significnatly boost the capabilities of PIA, as well as its synergy with APIA(another framework detailed on my profile)

## Contribution

mann just help out man we all gone go up anyways so if u think you can, you might as well put a lil sum in 

## License

(Add license information here)
```

This README focuses solely on v0.5's characteristics as you requested, drawing directly from the provided sources. Let me know if you'd like any modifications or further details added.
