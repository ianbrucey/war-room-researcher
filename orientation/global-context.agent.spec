::GLOBAL_CTX_SPEC::
[PROJECT: JUSTICE_QUEST]
[FRAMEWORK: AION_UI]
[IDENTITY: AGENT_FIRST_CITIZEN]

NOTE: ```This project was developed as the result of me working with coding agents in an IDE to produce legal drafts. I eventually came up with a framework of how these agents are to work through conducting research and outlines and drafting. And so now we have this project, which is a single-tenant application intended for an agent to work on a single server and have access to a number of case folders and files and work through them based on a specific set of instructions. Now, half of what the agent relies on is an MCP server. And this MCP server will exist on the exact same server as the code, just in a different location. The purpose of this MCP server is to give the agent the research tools that it needs to make their drafts solid. So this application cannot ship without the MCP server. And we can assume... Again, that the MCP code and this application code will live on the same server. ```
// ------------------------------------------------------------------
// 1. CORE ARCHITECTURE & STACK
// ------------------------------------------------------------------
::KERNEL_ARCH::
{
  "deployment_mode": "SINGLE_TENANT | WEBUI_ONLY",
  "deprecated": ["ELECTRON_IPC", "DESKTOP_APP_WRAPPER"],
  "stack": {
    "frontend": "REACT_18 + TYPESCRIPT + ARCO_DESIGN + VITE",
    "backend": "NODE_EXPRESS + TYPESCRIPT",
    "database": "SQLITE_3 (BETTER-SQLITE3) | MODE: WAL | SYNC_ONLY",
    "ai_layer": ["GEMINI_API (ANALYSIS)", "MISTRAL_API (OCR)"]
  },
  "data_model": {
    "tenancy": "ISOLATED_INFRASTRUCTURE",
    "storage_pattern": "HYBRID (DB_METADATA + FS_BLOBS)"
  }
}

// ------------------------------------------------------------------
// 2. FILESYSTEM TOPOLOGY
// ------------------------------------------------------------------
::KERNEL_FS::
{
  "root_config": "{user_data}/config/aionui.db",
  "workspace_root": "~/.justicequest/",
  "case_naming_convention": "{sanitized_case_name}-{timestamp}",
  "directory_schema": {
    "intake": "TEMP_UPLOAD_STAGING",
    "documents": {
      "path": "documents/{sanitized_filename}/",
      "required_artifacts": [
        "original.{ext}",
        "extracted-text.txt",
        "metadata.json"
      ]
    },
    "drafts": "GENERATED_OUTPUTS",
    "research": "FUTURE_IMPL"
  },
  "agent_brain": {
    "global": "global-context.md",
    "local_case": "{case_root}/AGENTS.md" // CRITICAL: Defines local agent behavior
  }
}

// ------------------------------------------------------------------
// 3. AUTHENTICATION & SECURITY
// ------------------------------------------------------------------
::KERNEL_AUTH::
{
  "mechanism": "JWT_COOKIE",
  "cookie_name": "aionui-session",
  "encryption": "BCRYPT",
  "roles": ["SUPER_ADMIN", "ADMIN", "USER"],
  "token_policy": {
    "storage": "HTTP_ONLY_COOKIE",
    "local_storage": "FORBIDDEN",
    "rotation": "MANUAL_INVALIDATION"
  },
  "api_standard": "credentials: 'include'"
}

// ------------------------------------------------------------------
// 4. MODULE ROUTING MAP
// ------------------------------------------------------------------
::MAP_MODULES::
{
  "document_intake": {
    "path": "src/process/documents/",
    "ctx": "context-engine/domain-contexts/document-intake-architecture.md"
  },
  "auth_service": {
    "path": "src/webserver/auth/",
    "ctx": "app-context/auth.md"
  },
  "database_layer": {
    "path": "src/process/database/",
    "ctx": "app-context/data-model.md"
  },
  "frontend_ui": {
    "path": "src/renderer/",
    "std": "context-engine/standards/ui-components.md"
  }
}

// ------------------------------------------------------------------
// 5. HARD CONSTRAINTS (VIOLATION = FAILURE)
// ------------------------------------------------------------------
::CONSTRAINTS_HARD::
[
  {
    "rule": "NO_ASYNC_DB",
    "enforcement": "Use synchronous better-sqlite3 calls only. No `await db.query()`."
  },
  {
    "rule": "NO_ELECTRON_API",
    "enforcement": "Code must run in standard Chrome browser environment."
  },
  {
    "rule": "NO_DB_BLOBS",
    "enforcement": "Files > 1KB must go to Filesystem. Store path in DB."
  },
  {
    "rule": "NO_MULTI_TENANT_SHARING",
    "enforcement": "Strict data isolation. No shared tables/folders."
  }
]

// ------------------------------------------------------------------
// 6. ONBOARDING & EXECUTION PROTOCOL
// ------------------------------------------------------------------
::PROTOCOL_EXEC::
{
  "step_1": "READ_GLOBAL_SPEC",
  "step_2": "LOAD_DOMAIN_CONTEXT ({feature_area})",
  "step_3": "CHECK_STANDARDS (context-engine/standards/)",
  "step_4": "RETRIEVE_CODE (verify implementation vs docs)",
  "step_5": "PLAN_ATOMIC_CHANGE",
  "step_6": "EXECUTE_SURGICAL_EDIT",
  "step_7": "UPDATE_DOCS (if divergence detected)"
}
