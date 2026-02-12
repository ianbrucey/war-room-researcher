# GPT Researcher: Research Modes Overview

This document provides an overview of the different research modes available in the GPT Researcher project.

## 1. Web Research

This is the default and primary research mode. It leverages web scraping to gather information from a multitude of online sources.

- **Process:** It takes a research query, generates a set of research questions, and then uses multiple crawler agents to browse the web and gather information to answer those questions.
- **Goal:** To produce a detailed, factual, and unbiased research report by aggregating information from over 20 sources. This helps to mitigate misinformation and provides a comprehensive overview of the topic.

## 2. Local Document Research

GPT Researcher can perform research tasks based on a collection of local documents provided by the user.

- **Supported Formats:** PDF, plain text, CSV, Excel, Markdown, PowerPoint, and Word documents.
- **Setup:** The user specifies a folder containing the documents by setting the `DOC_PATH` environment variable. The research is then sourced from these files instead of the web.
- **Use Case:** Ideal for analyzing internal reports, proprietary knowledge bases, or any collection of documents not available on the public internet.

## 3. MCP (Model-Context-Protocol) Integration

This mode allows for "hybrid research" by connecting GPT Researcher with specialized, structured data sources in addition to the standard web search.

- **Concept:** MCP enables the agent to query data sources like GitHub repositories, databases, or custom APIs.
- **Implementation:** The user can enable this mode by setting the `RETRIEVER` environment variable to include `mcp` (e.g., `tavily,mcp`). The specific data sources are configured via `mcp_configs`.
- **Use Case:** Enables research that requires information from both public web sources and specific, private, or structured data sets. For example, analyzing a software project by querying its GitHub repository and also searching for public documentation and articles about it.

## 4. Deep Research

Deep Research is an advanced, recursive workflow designed to explore topics with significant depth and breadth.

- **Methodology:** It employs a tree-like exploration pattern. The main research topic is broken down into sub-topics, and the agent dives deeper into each one, creating new branches of inquiry as it goes.
- **Features:**
    - Configurable depth and breadth for the research tree.
    - Concurrent processing of research branches for efficiency.
    - Smart context management to maintain coherence across the entire research task.
- **Use Case:** Suitable for complex topics that require a multi-faceted and in-depth investigation, going far beyond a surface-level summary.

## 5. Multi-Agent Research

Inspired by recent developments in multi-agent AI systems (like the STORM paper), this mode uses a team of specialized AI agents to collaborate on a research task.

- **Framework:** Built using LangGraph, it orchestrates a workflow between different agents, each with a specific role (e.g., planning, data gathering, analysis, writing).
- **Process:** The process involves multiple stages, from initial planning and outline generation to collaborative research and final report publication.
- **Outcome:** This approach aims to improve the depth and quality of the research by leveraging the specialized skills of multiple agents, resulting in comprehensive reports (often 5-6 pages) in various formats (PDF, Docx, Markdown).
- **Use Case:** For users who want the highest quality and most thorough research reports, leveraging a team of AI agents to simulate a human research team's workflow.
