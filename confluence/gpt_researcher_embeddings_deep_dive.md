# GPT Researcher: Embeddings & RAG Architecture Deep Dive

This document provides a detailed, refactor-ready breakdown of how GPT Researcher stores, embeds, and retrieves context from scraped web content and local documents. It answers the question: **"What exactly happens to text after it's scraped, and how does it get turned into useful context for the LLM?"**

---

## The Two Distinct Data Paths

GPT Researcher has **two separate paths** for turning raw content into context. Which path is used depends on whether the caller provides a `vector_store` object:

| Path | When Used | Storage | Persistence |
|---|---|---|---|
| **Path A: In-Memory Compression** | Default (web search, local docs without a vector store) | Python lists in RAM | **None** — ephemeral, discarded after the research run |
| **Path B: Vector Store** | When `vector_store` is explicitly passed to `GPTResearcher(...)` | Real vector DB (e.g., FAISS, Chroma, Pinecone) | **Persistent** — survives across runs |

> **Key Insight:** By default, GPT Researcher does **NOT** use a persistent vector database. All content lives in Python lists and is discarded when the run finishes. The vector store path is an opt-in feature.

---

## Path A: In-Memory Compression (Default)

This is the standard path for web research. No files are saved to disk, no vector DB is used.

### Step 1: Scraping → Raw Dicts

After the `Scraper` class fetches and cleans web pages, it returns a **list of Python dictionaries**:

```python
# Output of Scraper.run() — plain Python dicts, NOT stored anywhere
[
    {
        "url": "https://example.com/article",
        "raw_content": "The full cleaned text of the page...",
        "image_urls": ["https://example.com/img1.jpg"],
        "title": "Example Article Title"
    },
    ...
]
```

**File:** `gpt_researcher/scraper/scraper.py` → `Scraper.run()`

These dicts are passed directly to the next step. They are **not** converted to PDFs, not saved to disk, and not stored in any database.

### Step 2: Wrapping → LangChain Documents

The `SearchAPIRetriever` class (in `gpt_researcher/context/retriever.py`) wraps these raw dicts into LangChain `Document` objects. This is a **thin adapter** — it does not persist anything:

```python
# SearchAPIRetriever._get_relevant_documents()
docs = [
    Document(
        page_content=page.get("raw_content", ""),  # The scraped text
        metadata={
            "title": page.get("title", ""),
            "source": page.get("url", ""),
        },
    )
    for page in self.pages  # self.pages = the raw dicts from Step 1
]
```

**File:** `gpt_researcher/context/retriever.py` → `SearchAPIRetriever`

### Step 3: Chunking → Text Splits

The `ContextCompressor` (in `gpt_researcher/context/compression.py`) builds a LangChain pipeline. The first stage is a `RecursiveCharacterTextSplitter`:

```python
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
```

This splits each document's `page_content` into **chunks of ~1000 characters** with 100-character overlap between adjacent chunks. A single web page might produce 5-20 chunks depending on length.

**File:** `gpt_researcher/context/compression.py` → `ContextCompressor.__get_contextual_retriever()`

### Step 4: Embedding → Similarity Filtering

The second stage of the pipeline is an `EmbeddingsFilter`:

```python
relevance_filter = EmbeddingsFilter(
    embeddings=self.embeddings,           # From the Memory class
    similarity_threshold=self.similarity_threshold  # Default: 0.35
)
```

**What this does:**

1. **Embeds the query**: Converts the user's search query into a vector using the configured embedding model.
2. **Embeds each chunk**: Converts every text chunk from Step 3 into a vector.
3. **Calculates cosine similarity**: Compares each chunk's vector to the query's vector.
4. **Filters**: Only chunks with a similarity score ≥ `similarity_threshold` (default **0.35**, configurable via `SIMILARITY_THRESHOLD` env var) pass through.

> **Important:** These embeddings are computed **on-the-fly** and are **not stored anywhere**. They exist only in memory during the filtering step. Once filtering is done, only the text of the surviving chunks is kept — the vectors themselves are discarded.

**File:** `gpt_researcher/context/compression.py` → `ContextCompressor.__get_contextual_retriever()`

### Step 5: Formatting → Context String

The surviving chunks are formatted into a single context string using `pretty_print_docs`:

```python
# PromptFamily.pretty_print_docs()
"Source: https://example.com/article\n"
"Title: Example Article Title\n"
"Content: The relevant chunk of text...\n"
```

This string is what gets passed to the LLM as "context" in the report generation prompt.

**File:** `gpt_researcher/prompts.py` → `PromptFamily.pretty_print_docs()`

### Full Pipeline Diagram (Path A)

```
Web Pages (HTML)
    ↓ Scraper.run()
Raw Python Dicts [{"url": ..., "raw_content": ..., "title": ...}]
    ↓ SearchAPIRetriever (thin wrapper)
LangChain Document objects (in memory)
    ↓ RecursiveCharacterTextSplitter (chunk_size=1000, overlap=100)
Text Chunks (~1000 chars each)
    ↓ EmbeddingsFilter (similarity_threshold=0.35)
    │   ├── Embed query → vector
    │   ├── Embed each chunk → vector
    │   └── Keep chunks where cosine_similarity(query, chunk) >= 0.35
Relevant Chunks (filtered)
    ↓ pretty_print_docs()
Context String → sent to LLM for report generation
```

**Nothing is saved to disk. Nothing goes into a database. Everything is ephemeral.**

---

## Path B: Vector Store (Opt-In)

This path is used when the caller explicitly provides a `vector_store` parameter to `GPTResearcher(...)`. This is the "real RAG" path.

### When It Activates

```python
# In researcher.py, after scraping or loading documents:
if self.researcher.vector_store:
    self.researcher.vector_store.load(scraped_content)  # <-- loads into DB
```

### Step 1: Wrapping → LangChain Documents

The `VectorStoreWrapper.load()` method converts the raw dicts into LangChain Documents:

```python
# VectorStoreWrapper._create_langchain_documents()
Document(
    page_content=item["raw_content"],
    metadata={"source": item["url"]}
)
```

**File:** `gpt_researcher/vector_store/vector_store.py` → `VectorStoreWrapper._create_langchain_documents()`

### Step 2: Chunking

Same strategy as Path A, but with slightly different parameters:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200  # NOTE: 200 overlap vs 100 in Path A
)
```

**File:** `gpt_researcher/vector_store/vector_store.py` → `VectorStoreWrapper._split_documents()`

### Step 3: Storage → Vector Database

The chunked documents are added to the actual vector store:

```python
self.vector_store.add_documents(splitted_documents)
```

This is where the real persistence happens. The underlying `self.vector_store` is a LangChain-compatible vector store (FAISS, Chroma, Pinecone, etc.) that:
1. **Embeds** each chunk using the configured embedding model.
2. **Stores** the vector + original text in the database.
3. **Persists** across the research session (and potentially across runs, depending on the backend).

**File:** `gpt_researcher/vector_store/vector_store.py` → `VectorStoreWrapper.load()`

### Step 4: Retrieval → Similarity Search

When context is needed, the `VectorstoreCompressor` queries the vector store:

```python
# VectorstoreCompressor.async_get_context()
results = await self.vector_store.asimilarity_search(
    query=query,
    k=max_results,  # Default: 5-8 results
    filter=self.filter
)
```

This returns the top-k most similar chunks from the database.

**File:** `gpt_researcher/context/compression.py` → `VectorstoreCompressor.async_get_context()`

### Full Pipeline Diagram (Path B)

```
Web Pages (HTML) or Local Documents
    ↓ Scraper.run() or DocumentLoader.load()
Raw Python Dicts [{"url": ..., "raw_content": ..., "title": ...}]
    ↓ VectorStoreWrapper._create_langchain_documents()
LangChain Document objects
    ↓ RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
Text Chunks
    ↓ vector_store.add_documents()
    │   ├── Embed each chunk → vector (via configured embedding model)
    │   └── Store vector + text in database (FAISS/Chroma/Pinecone/etc.)
PERSISTED IN VECTOR DATABASE
    ↓ vector_store.asimilarity_search(query, k=5)
Top-k Most Similar Chunks
    ↓ pretty_print_docs()
Context String → sent to LLM for report generation
```

---

## The Embedding Model

The embedding model is configured in `gpt_researcher/memory/embeddings.py` via the `Memory` class.

### Default Configuration

```python
# Default embedding model (from env var or hardcoded fallback)
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
```

### How It's Initialized

```python
# In agent.py line 173
self.memory = Memory(
    self.cfg.embedding_provider,   # e.g., "openai"
    self.cfg.embedding_model,      # e.g., "text-embedding-3-small"
    **self.cfg.embedding_kwargs
)
```

### Supported Providers (17+)

| Provider | LangChain Class | Config Key |
|---|---|---|
| `openai` | `OpenAIEmbeddings` | Default |
| `azure_openai` | `AzureOpenAIEmbeddings` | Needs `AZURE_OPENAI_*` env vars |
| `cohere` | `CohereEmbeddings` | |
| `google_vertexai` | `VertexAIEmbeddings` | |
| `google_genai` | `GoogleGenerativeAIEmbeddings` | |
| `ollama` | `OllamaEmbeddings` | Needs `OLLAMA_BASE_URL` |
| `huggingface` | `HuggingFaceEmbeddings` | |
| `voyageai` | `VoyageAIEmbeddings` | Needs `VOYAGE_API_KEY` |
| `bedrock` | `BedrockEmbeddings` | AWS Bedrock |
| `custom` | `OpenAIEmbeddings` (custom base URL) | For local models (LMStudio, etc.) |
| ... | ... | See `Memory` class for full list |

**File:** `gpt_researcher/memory/embeddings.py`

### Where Embeddings Are Used

1. **ContextCompressor** (Path A): Uses `self.researcher.memory.get_embeddings()` to get the embedding model, then passes it to the `EmbeddingsFilter` for on-the-fly similarity filtering.
2. **VectorStoreWrapper** (Path B): The vector store itself uses the embedding model (configured separately when the vector store is created) to embed chunks before storing them.
3. **WrittenContentCompressor**: Uses embeddings to find similar previously-written content sections (for detailed reports with multiple subtopics).

---

## Configuration Reference

| Setting | Env Var | Default | Purpose |
|---|---|---|---|
| Embedding Provider | `EMBEDDING_PROVIDER` | `openai` | Which embedding API to use |
| Embedding Model | `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Which model to embed with |
| Similarity Threshold | `SIMILARITY_THRESHOLD` | `0.35` | Minimum cosine similarity for chunk inclusion (Path A) |
| Chunk Size (Path A) | Hardcoded | `1000` chars | Text chunk size for compression pipeline |
| Chunk Overlap (Path A) | Hardcoded | `100` chars | Overlap between adjacent chunks |
| Chunk Size (Path B) | Hardcoded | `1000` chars | Text chunk size for vector store |
| Chunk Overlap (Path B) | Hardcoded | `200` chars | Overlap between adjacent chunks |

---

## Key Files for Refactoring

| File | What It Does | When to Modify |
|---|---|---|
| `gpt_researcher/context/compression.py` | Builds the chunking + embedding + filtering pipeline | Change chunk sizes, similarity thresholds, or swap out the filtering strategy |
| `gpt_researcher/context/retriever.py` | Wraps raw dicts into LangChain Documents | Change how scraped data is structured or add metadata |
| `gpt_researcher/memory/embeddings.py` | Creates the embedding model instance | Add new embedding providers or change defaults |
| `gpt_researcher/vector_store/vector_store.py` | Manages the optional persistent vector store | Change chunking for vector DB, add indexing strategies, or swap vector backends |
| `gpt_researcher/skills/context_manager.py` | Orchestrates which compression path to use | Change how context is requested or add caching |
| `gpt_researcher/skills/researcher.py` (lines 140-230) | Decides whether to use Path A or B based on `report_source` and `vector_store` | Change the routing logic to always use a vector store, or add a new path |
