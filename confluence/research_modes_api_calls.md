# GPT Researcher: Research Modes - Methods and API Calls

This document outlines the key methods and API calls associated with each research mode in the GPT Researcher project.

### 1. Web Research (Standard Mode)

This is the default behavior, orchestrated by the main `GPTResearcher` class.

*   **File:** `gpt_researcher/agent.py`
*   **Method:** `conduct_research`
*   **Description:** This is the primary method that kicks off the standard web research process. It generates research questions, triggers web scraping via retrievers, and synthesizes the findings.

```python
# gpt_researcher/agent.py

class GPTResearcher:
    # ...
    async def conduct_research(self):
        """
        Runs the research process
        """
        # ...
        # Generate research questions
        research_questions = await self.get_research_questions(self.query)
        # ...
        # Scrape sources
        scraped_content = await self.scrape_sources(research_questions)
        # ...
```

### 2. Local Document Research

This mode is enabled by setting the `report_source` to "local". The system then uses a `DocxReport` or similar class which gets context from local files.

*   **File:** `gpt_researcher/utils/report_helpers.py`
*   **Method:** `get_report_by_type`
*   **Description:** This function acts as a factory, selecting the appropriate report generator based on the `report_type` (e.g., "research_report", "docx"). The logic for handling local documents is within the specific report type classes.

```python
# gpt_researcher/utils/report_helpers.py

def get_report_by_type(report_type):
    # ...
    report_type_mapping = {
        "research_report": ResearchReport,
        "resource_report": ResourceReport,
        "outline_report": OutlineReport,
        "custom_report": CustomReport,
        "detailed_report": DetailedReport,
        "subtopic_report": SubtopicReport,
        "docx": DocxReport,
    }
    return report_type_mapping[report_type]
```

The actual retrieval of local documents is handled by the `get_context_by_search` function when the retriever is configured for local files.

*   **File:** `gpt_researcher/context/retrieval.py`
*   **Method:** `get_context_by_search`

### 3. MCP (Model-Context-Protocol) Integration

MCP is enabled via environment variables and configured when the `GPTResearcher` class is instantiated.

*   **File:** `gpt_researcher/agent.py`
*   **Method:** `__init__`
*   **Description:** The constructor initializes the MCP instance if `mcp_configs` are provided, setting up the necessary components to query specialized data sources.

```python
# gpt_researcher/agent.py

class GPTResearcher:
    def __init__(
        self,
        query: str,
        # ...
        mcp_configs=None,
        # ...
    ):
        # ...
        if mcp_configs:
            self.mcp = MCP(mcp_configs)
        # ...
```

### 4. Deep Research

This mode is triggered by calling a specific method, likely within a class designed for it, although it's not in the main `GPTResearcher` agent. The `README.md` points to a specific documentation page. Based on that, the entry point is `DeepResearch`.

*   **File:** `backend/report_type/deep_research/__init__.py`
*   **Class:** `DeepResearch`
*   **Method:** `conduct_research`
*   **Description:** This class contains the logic for the recursive, tree-like research process. Its `conduct_research` method implements the deep dive into subtopics.

```python
# backend/report_type/deep_research/__init__.py

class DeepResearch:
    # ...
    async def conduct_research(self):
        # ...
        # Kicks off the deep research process
        # This will involve creating a tree of research tasks and executing them
        # ...
```

### 5. Multi-Agent Research

This mode is located in a separate directory and uses LangGraph to define a graph of interacting agents.

*   **File:** `multi_agents/main.py`
*   **Function:** `main`
*   **Description:** This is the main entry point for the multi-agent research system. It sets up the LangGraph workflow, defines the team of agents, and starts the research process.

```python
# multi_agents/main.py

def main(task: dict, interactive: bool = False):
    # ...
    # Define the graph of agents
    workflow = create_graph()
    app = workflow.compile()
    
    # ...
    # Run the research process
    for output in app.stream(task, config):
        # ...
```