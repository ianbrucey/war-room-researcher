# Implementation Plan: Case Documents Integration

**Status**: Planning  
**Created**: 2026-02-12  
**Related Docs**: 
- `confluence/proposal_agent_based_synthesis.md`
- `confluence/decision_subquery_generation.md`

---

## 1. Overview

This document outlines the implementation plan for adding `case_documents` parameter to GPT Researcher, enabling the synthesis agent to access case-specific documents during report generation.

### Problem Statement

Currently, GPT Researcher only uses web-scraped research for report generation. For legal research in WarRoom, we need to combine:
- **Web research** (general legal principles, case law, statutes)
- **Case-specific documents** (motion, complaint, contract, ATTACKS.json, INTENT.md)

The synthesis agent needs access to both sources to produce contextually relevant legal research reports.

### Solution

Add a `case_documents` parameter to `GPTResearcher.__init__()` that accepts a dictionary of document paths. These paths will be:
1. Stored in the researcher instance
2. Ignored during sub-query generation and web scraping phases
3. Passed to the synthesis agent during report generation

---

## 2. Architecture

### Data Flow

```
WarRoom Application
    ↓ (provides case_documents dict)
GPTResearcher.__init__()
    ↓ (stores as self.case_documents)
Sub-query Generation (ignores case_documents)
    ↓
Web Search & Scrape (ignores case_documents)
    ↓
Curation Agent (ignores case_documents)
    ↓
Synthesis Agent (USES case_documents)
    ↓
Final Report
```

### Case Documents Structure

```python
case_documents = {
    # Core legal documents
    "motion": "/path/to/motion_to_dismiss/extracted-text.txt",
    "complaint": "/path/to/complaint/extracted-text.txt",
    "answer": "/path/to/answer/extracted-text.txt",
    "contract": "/path/to/contract/extracted-text.txt",
    
    # Strategy documents
    "attacks_json": "/path/to/ATTACKS.json",
    "intent_md": "/path/to/INTENT.md",
    "gap_analysis": "/path/to/GAP_ANALYSIS.md",
    
    # Evidence
    "evidence_analysis": "/path/to/EVIDENCE_ANALYSIS.json",
    
    # Custom documents (flexible)
    "custom_memo": "/path/to/custom_memo.txt"
}
```

**Design Principles**:
- **Flexible keys**: No required keys, WarRoom decides what to include
- **Absolute paths**: Full file paths for clarity
- **Optional parameter**: Backward compatible (defaults to empty dict)

---

## 3. Implementation Steps

### Step 1: Add Parameter to `agent.py`

**File**: `gpt_researcher/agent.py`  
**Location**: `__init__()` method (line 51-83)

**Changes**:
1. Add `case_documents: dict | None = None` parameter after `context_packet`
2. Store as `self.case_documents = case_documents or {}`
3. Add validation to ensure paths exist (optional, can be added later)

**Rationale**:
- Follows same pattern as `context_packet` (added in previous enhancement)
- Uses `dict | None` type hint for Python 3.10+ compatibility
- Defaults to empty dict for backward compatibility

### Step 2: Document the Parameter

**File**: `gpt_researcher/agent.py`  
**Location**: Docstring for `__init__()` method

**Add**:
```python
case_documents (dict, optional): Dictionary mapping document types to file paths.
    Used by synthesis agent to access case-specific documents.
    Example: {"motion": "/path/to/motion.txt", "complaint": "/path/to/complaint.txt"}
    Defaults to None (empty dict).
```

### Step 3: Update Configuration (Future)

**File**: `gpt_researcher/config/variables/default.py`

**Add** (in future PR when synthesis agent is implemented):
```python
"CASE_DOCUMENTS_VALIDATION": True,  # Validate file paths exist
"CASE_DOCUMENTS_MAX_SIZE_MB": 50,   # Max total size of case documents
```

---

## 4. Integration Points

### Current Integration (This PR)

**Phase**: Storage only
- `agent.py`: Store `case_documents` in `self.case_documents`
- No other files modified
- No functional changes to research flow

### Future Integration (Synthesis Agent PR)

**Phase**: Usage in synthesis
- `writer.py`: Pass `self.researcher.case_documents` to synthesis agent
- `context_manager.py`: Optionally validate file paths before synthesis
- Synthesis agent CLI: Read files from provided paths

---

## 5. Backward Compatibility

### Existing Code (No Breaking Changes)

```python
# Current usage (still works)
researcher = GPTResearcher(
    query="Research AI ethics",
    context_packet={...}
)
```

### New Usage (Optional Parameter)

```python
# New usage with case documents
researcher = GPTResearcher(
    query="Research standing defenses",
    context_packet={...},
    case_documents={
        "motion": "/path/to/motion.txt",
        "complaint": "/path/to/complaint.txt"
    }
)
```

**Guarantee**: All existing code continues to work without modification.

---

## 6. Testing Strategy

### Unit Tests (This PR)

```python
def test_case_documents_parameter():
    """Test case_documents parameter is stored correctly."""
    docs = {"motion": "/tmp/motion.txt", "complaint": "/tmp/complaint.txt"}
    researcher = GPTResearcher(query="test", case_documents=docs)
    assert researcher.case_documents == docs

def test_case_documents_defaults_to_empty_dict():
    """Test case_documents defaults to empty dict when not provided."""
    researcher = GPTResearcher(query="test")
    assert researcher.case_documents == {}
```

### Integration Tests (Future PR)

- Test synthesis agent reads case documents correctly
- Test handling of missing files
- Test handling of large files (> 50MB)

---

## 7. Timeline

### Phase 1: Parameter Addition (This PR)
- **Duration**: 1 day
- **Scope**: Add parameter, store in instance, add tests
- **Files Modified**: `gpt_researcher/agent.py`
- **Risk**: Low (storage only, no functional changes)

### Phase 2: Synthesis Integration (Future PR)
- **Duration**: 1-2 weeks
- **Scope**: Implement synthesis agent, integrate case documents
- **Files Modified**: `writer.py`, `context_manager.py`, synthesis agent CLI
- **Risk**: Medium (new functionality, requires testing)

---

## 8. Success Criteria

### This PR
- ✅ `case_documents` parameter added to `GPTResearcher.__init__()`
- ✅ Parameter stored in `self.case_documents`
- ✅ Defaults to empty dict when not provided
- ✅ Unit tests pass
- ✅ No breaking changes to existing code

### Future PR (Synthesis Agent)
- ✅ Synthesis agent reads case documents from provided paths
- ✅ Report quality improves with case-specific context
- ✅ Integration tests pass on 10 real WarRoom cases

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **File paths invalid** | Synthesis fails | Add validation in future PR, fail gracefully |
| **Files too large** | Memory issues | Add size limits in config (future PR) |
| **Breaking changes** | Existing code breaks | Use optional parameter with default value |
| **Unused parameter** | Code bloat | Document clearly, implement synthesis soon |

---

## 10. Next Steps

1. ✅ Create this implementation plan
2. ⏳ Implement `case_documents` parameter in `agent.py`
3. ⏳ Add unit tests
4. ⏳ Update documentation
5. ⏳ Review and merge PR
6. 🔜 Plan synthesis agent implementation (separate PR)

---

## Appendix: Example Usage in WarRoom

```python
# In WarRoom controller (strategy_relay_defensive.py)
def call_gpt_researcher(case_workspace: str, research_query: str):
    """Call GPT Researcher API with case documents."""
    
    # Build case documents dict
    case_docs = {
        "motion": f"{case_workspace}/documents/motion_to_dismiss/extracted-text.txt",
        "complaint": f"{case_workspace}/documents/complaint/extracted-text.txt",
        "attacks": f"{case_workspace}/strategies/001_defensive/ATTACKS.json",
        "intent": f"{case_workspace}/strategies/001_defensive/INTENT.md"
    }
    
    # Call GPT Researcher
    researcher = GPTResearcher(
        query=research_query,
        context_packet=build_context_packet(),
        case_documents=case_docs
    )
    
    report = await researcher.conduct_research()
    return report
```

