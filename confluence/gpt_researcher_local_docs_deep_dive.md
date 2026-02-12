# GPT Researcher: Local Document Handling Deep Dive

This document details how GPT Researcher ingests and processes local files when `REPORT_SOURCE` is set to `local` or `hybrid`.

---

## 1. The Entry Point: `DOC_PATH`

To use local documents, you must set the `DOC_PATH` environment variable or configuration to a directory path.

When `report_source` is set to "local", the `ResearchConductor` (in `gpt_researcher/skills/researcher.py`) initiates the loading process:

```python
# gpt_researcher/skills/researcher.py

elif self.researcher.report_source == ReportSource.Local.value:
    # Load all documents from the configured path
    document_data = await DocumentLoader(self.researcher.cfg.doc_path).load()
```

---

## 2. The Loader Logic (`DocumentLoader`)

**File:** `gpt_researcher/document/document.py`

The `DocumentLoader` is responsive for:
1.  Scanning the directory (recursively).
2.  Identifying file types.
3.  Extracting text using appropriate parsers.

### Recursive Scanning

It uses `os.walk` to traverse the directory tree, meaning it will find files in subdirectories as well.

```python
for root, dirs, files in os.walk(self.path):
    for file in files:
        # ... process file ...
```

### Supported File Types

The loader maps file extensions to specific **LangChain** document loaders. If a file extension is not in this list, it is ignored.

| Extension | Loader Class |
|---|---|
| `.pdf` | `PyMuPDFLoader` |
| `.txt` | `TextLoader` |
| `.doc`, `.docx` | `UnstructuredWordDocumentLoader` |
| `.pptx` | `UnstructuredPowerPointLoader` |
| `.csv` | `UnstructuredCSVLoader` |
| `.xls`, `.xlsx` | `UnstructuredExcelLoader` |
| `.md` | `UnstructuredMarkdownLoader` |
| `.html`, `.htm` | `BSHTMLLoader` |

### Output Format

The `load()` method returns a list of dictionaries, normalized to match the format of scraped web pages:

```python
[
    {
        "raw_content": "The full text content of the file...",
        "url": "filename.pdf"  # The filename acts as the 'url' or source
    },
    ...
]
```

### Deep Dive: PDF Handling (`PyMuPDFLoader`)

PDFs receive special treatment that's important to understand for context quality.

1.  **Page-by-Page Slicing**:
    *   `PyMuPDFLoader` (from LangChain) reads the PDF.
    *   It creates a separate **Document object for every single page**.
    *   It does **not** concatenate these pages back into a single "file" object.

2.  **Flattening**:
    *   The `DocumentLoader.load()` loop iterates through these pages.
    *   **Result**: A 10-page PDF becomes **10 separate items** in the `document_data` list.
    *   Each item shares the same filename in its `url` field.

    ```python
    # Example of a loaded 2-page PDF
    [
        {"raw_content": "Text from Page 1...", "url": "report.pdf"},
        {"raw_content": "Text from Page 2...", "url": "report.pdf"}
    ]
    ```

3.  **Implications**:
    *   **Context Fragmentation**: If a sentence or paragraph spans across a page break, it gets split into two separate context chunks.
    *   **No "Whole Doc" Understanding**: The LLM never sees the PDF as a single cohesive unit; it only sees isolated pages (or chunks of pages) that happen to match the query.
    *   **Images**: By default, `PyMuPDFLoader` extracts **text only**. Diagrams and charts inside the PDF are ignored unless they have selectable text layers.

---

## 3. Integration with the Research Pipeline

This is the most critical part of the architecture: **Local documents are treated exactly like scraped web pages.**

After loading the documents, `ResearchConductor` passes them to `_get_context_by_web_search` as the `scraped_data` argument:

```python
# gpt_researcher/skills/researcher.py

# Pass local docs as if they were scraped from the web
research_data = await self._get_context_by_web_search(
    query=self.researcher.query, 
    scraped_data=document_data  # <--- Local docs injected here
)
```

Inside `_get_context_by_web_search`:
1.  It skips the web scraping step (since `scraped_data` is already provided).
2.  It sends the data to `ContextManager.get_similar_content_by_query`.
3.  The **same** chunking, embedding, and similarity filtering logic described in the **Embeddings Deep Dive** is applied.

> **Key Takeaway:** You don't need a separate "local document pipeline." The system reuses the efficient "Context Compression" pipeline by standardizing the input format.

---

## 4. Hybrid Research (`local` + `web`)

When `report_source` is set to "hybrid":

1.  **Local Step**: Loads documents from `DOC_PATH`.
2.  **Web Step**: Performs a standard web search and scrape.
3.  **Combination**: Both sets of context are gathered.

```python
# gpt_researcher/skills/researcher.py

# 1. Load Local
document_data = await DocumentLoader(self.researcher.cfg.doc_path).load()

# 2. Process Local Context
docs_context = await self._get_context_by_web_search(self.researcher.query, document_data)

# 3. Process Web Context (scraped_data=[] forces new search)
web_context = await self._get_context_by_web_search(self.researcher.query, [])

# 4. Join Results
research_data = self.researcher.prompt_family.join_local_web_documents(docs_context, web_context)
```

---

## 5. Potential Issues & Customization

### Performance with Large Libraries
Because `DocumentLoader` loads **all** files into memory before filtering, pointing `DOC_PATH` to a massive directory (e.g., 10GB of PDFs) will likely cause an **Out of Memory (OOM)** error.

**Refactoring Tip:** To handle large local libraries, you should:
1.  Use the **Vector Store** path (see Embeddings Deep Dive), which indexes chunks once and retrieves only relevant ones.
2.  Modify `DocumentLoader` to yield documents lazily (though the downstream context manager currently expects a full list).

### Adding New File Types
To support a new file type (e.g., `.epub`):
1.  Import the appropriate loader in `gpt_researcher/document/document.py`.
2.  Add the extension and loader to the `loader_dict` in `_load_document`.

```python
loader_dict = {
    # ... existing ...
    "epub": UnstructuredEPubLoader(file_path),
}
```
