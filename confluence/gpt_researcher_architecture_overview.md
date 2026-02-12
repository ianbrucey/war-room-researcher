# GPT Researcher: Architecture Overview & Modifying Behavior

This document outlines the internal mechanics of GPT Researcher, focusing on how research is conducted, how sources are selected, and how to customize its behavior.

## 1. How Research Happens Under the Hood

The core research loop is orchestrated by the `ResearchConductor` class in `gpt_researcher/skills/researcher.py`. The process follows these stages:

1.  **Planning**: The `plan_research` method generates a set of sub-queries based on the user's main query. This breaks down a complex topic into searchable chunks.
2.  **Retrieval**: `ResearchConductor` uses configured **Retrievers** (e.g., Tavily, Google, Bing) to execute these sub-queries and find relevant URLs.
3.  **Scraping**: The **BrowserManager** (using Selenium or Playwright) visits the identified URLs and scrapes their content.
4.  **Contextualization & Curating**: The `ContextManager` and `SourceCurator` filter and summarize the scraped content, selecting the most relevant information to form a "context".
5.  **Generation**: The `ReportGenerator` (in `gpt_researcher/skills/writer.py`) uses an LLM to synthesis the gathered context into a final report.

### Deep Dive: Planning & Query Generation

The "Planning" phase is critical for determining what information the agent looks for. This logic resides in `gpt_researcher/actions/query_processing.py`.

*   **Function**: `plan_research_outline` (and `generate_sub_queries`).
*   **Prompt**: The `generate_search_queries_prompt` in `gpt_researcher/prompts.py` is used.
*   **Prompt Structure**:
    ```text
    Write {max_iterations} google search queries to search online that form an objective opinion from the following task: "{task}"
    Assume the current date is {current_date} if required.
    You must respond with a list of strings in the following format: ["query 1", "query 2", "query 3"].
    The response should contain ONLY the list.
    ```
*   **Sub-Query Count**: The number of search queries generated is controlled by the `max_iterations` parameter in `config.py` (default is usually 3 or 4). This means for every user query, the LLM generates 3-4 distinct search queries (e.g., "benefits of AI", "risks of AI", "AI regulation").
*   **Search Nodes**: Each of these sub-queries effectively becomes a "search node," triggering its own web search and scraping process.

### Deep Dive: Retrieval & Scraping

Once sub-queries are generated, the agent moves to execution:

1.  **Retrieval**:
    *   **Tavily**: The default `TavilySearch` retriever (`gpt_researcher/retrievers/tavily/tavily_search.py`) hits the Tavily API.
    *   **Parameters**: It typically requests `search_depth="basic"`, `max_results=10`, and `include_domains` if specified.
    *   **Result**: It returns a list of dictionaries containing `url` and `body` (snippet).

2.  **Scraping**:
    *   **Scraper Class**: The `Scraper` class in `gpt_researcher/scraper/scraper.py` manages the process.
    *   **Selection Logic**: It selects a specific scraper based on the file type:
        *   `pdf`: Uses `PyMuPDFScraper`.
        *   `arxiv`: Uses `ArxivScraper`.
        *   **General Web**: Uses `BeautifulSoupScraper` (fast, static) or `BrowserScraper` (Selenium/Playwright for dynamic JS sites).
    *   **BrowserScraper**: Found in `gpt_researcher/scraper/browser/browser.py`, this spins up a headless Chrome/Firefox driver, visits the page, waits for `body` to load, and scrolls to the bottom to trigger lazy-loaded content before extracting the HTML.
    *   **Content Cleaning**: The HTML is then parsed (usually by `BeautifulSoup`), and script/style tags are removed to extract clean text.

### Deep Dive: Contextualization & Generation

After scraping, the raw text needs to be processed into a usable format:

1.  **Context Compression**:
    *   **ContextManager**: `gpt_researcher/skills/context_manager.py` orchestrates this.
    *   **ContextCompressor**: In `gpt_researcher/context/compression.py`, the `ContextCompressor` class handles the heavy lifting.
    *   **Embeddings**: It uses embeddings (via `SearchAPIRetriever` and `EmbeddingsFilter`) to calculate the similarity between the user's query and chunks of the scraped text.
    *   **Filtering**: Only text chunks that meet a certain `similarity_threshold` (default 0.35, configurable via env var) are kept. This reduces noise and token usage.

2.  **Report Generation**:
    *   **ReportGenerator**: `gpt_researcher/skills/writer.py` manages the writing process.
    *   **Prompt**: It calls `generate_report` in `gpt_researcher/actions/report_generation.py`, which selects the appropriate prompt from `gpt_researcher/prompts.py` (e.g., `generate_report_prompt` or `generate_deep_research_prompt`).
    *   **Synthesis**: The LLM is provided with the compressed "Context" and the original query to generate the final report, introduction, and conclusion.

## 2. How Agents Know Which Websites to Visit

Agents do not rely on a static list of websites. They dynamically discover sources using **Retrievers**.

*   **Mechanism**: The `get_retrievers` function in `gpt_researcher/actions/retriever.py` instantiates a specific search provider.
*   **Default**: The default retriever is usually `TavilySearch`, but this is configurable.
*   **Process**: The retriever takes a query (e.g., "latest advancements in quantum computing"), hits a search API, and returns a list of URLs. The agent then scrapes these specific URLs.

**To Modify Source Selection:**
*   **Configuration**: Change the `RETRIEVER` environment variable or the `retriever` setting in `config/config.py`. Options include `google`, `bing`, `duckduckgo`, `serpapi`, `google_news`, `arxiv`, etc.
*   **Custom Retrievers**: You can implement a custom retriever in `gpt_researcher/retrievers/` if you need to query a specific internal API or database.

## 3. How to Modify Search Behavior

To change *how* the agent searches or processes results:

*   **Modify Retrievers**: Edit the specific retriever class in `gpt_researcher/retrievers/`. For example, you can adjust `TavilySearch` to use different search parameters (like `search_depth` or `include_domains`).
*   **Modify Planning**: The logic for generating sub-queries is in `gpt_researcher/actions/query_processing.py`. You can adjust the prompts there to change how the agent breaks down tasks (e.g., to be more broad or more specific).
*   **Filter Domains**: You can pass a list of `query_domains` to restrict searches to specific sites (e.g., only `gov` or `edu` sites).

## 4. How to Modify Response Structure

To change the format, tone, or structure of the final report:

*   **Prompts**: The primary instructions for the LLM are located in `gpt_researcher/prompts.py`.
    *   `generate_report_prompt`: Controls the final report generation.
    *   `generate_search_summary_prompt`: Controls how search results are summarized.
*   **Report Generator**: The `write_report` method in `gpt_researcher/skills/writer.py` assembles the report. You can modify this to change the order of sections, add custom headers, or enforce specific stylistic rules.

## 5. Local Document Handling (`DOC_PATH`)

GPT Researcher can ingest local files instead of (or in addition to) web search.

*   **Activation**: Set the `DOC_PATH` environment variable to a directory containing your documents.
*   **Loading Logic**:
    *   When `report_source` is set to `local` or `hybrid`, the `ResearchConductor` uses `DocumentLoader` (in `gpt_researcher/document/document.py`).
    *   It recursively scans `DOC_PATH` and loads standard file formats: `.txt`, `.pdf`, `.docx`, `.pptx`, `.md`, `.csv`, `.xlsx`, `.html`.
*   **Vector Store**: Loaded documents are typically chunked and indexed into a local vector store for semantic retrieval during the "Contextualization" phase.

**To Modify Local Search:**
*   **File Support**: Extend `DocumentLoader` in `gpt_researcher/document/document.py` to support additional file extensions or custom parsing logic.
*   **Retrieval Strategy**: Modify how `ResearchConductor` queries the local vector store (e.g., changing `k` nearest neighbors or similarity thresholds).
