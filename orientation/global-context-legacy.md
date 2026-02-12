# Justice Quest: Global Context

## 1. Project Identity & Intention

**Identity**: You are building **Justice Quest** (powered by the AionUi framework).

- **We are not building a tool for lawyers to "use."**
- **We are building autonomous agents that "do" the work of a lawyer.**

**Intention**: The goal is to create a "Zero-Ambiguity" environment where AI agents are **First-Class Citizens**. The entire system architecture—from file storage to background processes—is designed specifically to serve *your* needs as an agent.

**The Philosophy**: "Agent-Embedded Framework"

- The file system is your eyes.
- The background services are your hands.
- The instructions are your brain.
- You do not "help" the user; you **execute** the work.

## 2. Problem Definition & Scope

**Problem Statement**: Legal professionals need an intelligent, agentic framework that can accurately and efficiently draft legal documents through file-based workflows, prompts, and protocols. Traditional legal document generation is time-consuming, error-prone, and requires extensive manual review.

**Project Scope**:

- **In Scope**: Document intake, text extraction, AI-powered analysis, legal document generation, case file management, multi-user collaboration within a single tenant
- **Out of Scope**: Multi-tenant SaaS deployment (each tenant requires dedicated infrastructure), real-time collaboration features, mobile applications

**Target Users**: Legal professionals (attorneys, paralegals, legal assistants) working within a single law firm or legal department

**Success Metrics**:

- Document processing accuracy and speed
- Time saved in legal document drafting
- User adoption within law firms
- Quality of AI-generated legal content

## Solution Architecture

**Architecture Pattern**: Monolithic WebUI application with embedded database and file-based storage

**Technology Stack**:

- **Frontend**: React 18 + TypeScript, Arco Design UI components, Vite bundler
- **Backend**: Node.js + Express, TypeScript
- **Database**: SQLite (via `better-sqlite3`) with WAL mode
- **Infrastructure**: Single-tenant deployment, local file storage, WebUI-only (Electron architecture deprecated)
- **AI Services**: Gemini API (document analysis), Mistral API (OCR/text extraction)

**Key Architectural Decisions**:

1. **WebUI-Only Deployment** (2025-12-13)

   - **Decision**: Application runs exclusively in browser-based WebUI mode. Original Electron desktop app architecture is deprecated.
   - **Rationale**: Simplifies deployment, reduces maintenance burden, enables easier updates, and aligns with modern web-first approach.
   - **Impact**: All new features must be designed for WebUI. No IPC bridge or Electron APIs should be used in new code.
2. **Single-Tenant Architecture** (2025-12-13)

   - **Decision**: One firm = one tenant, with dedicated infrastructure per tenant (separate database, workspace, file storage).
   - **Rationale**: Legal data requires strict isolation for confidentiality and compliance. Single-tenant model ensures complete data separation.
   - **Impact**: No shared resources between tenants. Each deployment is independent. Multi-user support exists within a single tenant only.
3. **Embedded SQLite Database** (2025-12-13)

   - **Decision**: Use SQLite with synchronous operations instead of PostgreSQL/MySQL.
   - **Rationale**: Single-tenant model doesn't require distributed database. SQLite provides excellent performance for local operations and simplifies deployment.
   - **Impact**: All database operations are synchronous. No ORM layer. Migration to server-based database would require major async refactor.
4. **File-Based Document Storage** (2025-12-13)

   - **Decision**: Store documents in filesystem at `~/.justicequest/{case-name-timestamp}/documents/{folder_name}/` instead of database BLOBs.
   - **Rationale**: Keeps database lightweight, enables direct file access, simplifies backup/restore, and improves performance.
   - **Impact**: Document paths must be tracked in database. File operations require filesystem access.

## 4. Core Mission & Purpose

**AionUi is an Agent-Embedded Framework** designed to give autonomous agents the "Physicality" they need to do real work.

**Why this Architecture?**
In a traditional app, the backend serves the UI. In Justice Quest, **the backend serves the Agent**.

- We extract text so *you* can read it.
- We keep original PDFs so *you* can see them (via Vision).
- We index documents so *you* can recall them (via RAG).
- We structure folders so *you* can navigate them.

**Primary Use Cases**:

- Document intake and processing (PDF, DOCX, TXT)
- Text extraction and OCR
- AI-powered document analysis and metadata generation
- Legal document generation and drafting
- Case file management and organization
- Multi-user collaboration within a single law firm

**Agent Philosophy**: Agents should treat document generation and legal workflow automation as the primary use case. All features should support the goal of helping legal professionals work more efficiently and accurately.

## Module Breakdown & Responsibilities

**Core Modules**:

1. **Document Intake Pipeline** (`src/process/documents/`, `src/webserver/routes/documentRoutes.ts`)

   - **Purpose**: Handle document upload, text extraction, AI analysis, and RAG indexing
   - **Responsibilities**: File upload, OCR/text extraction, metadata generation, document storage
   - **Domain Context**: `context-engine/domain-contexts/document-intake-architecture.md`
2. **Authentication & Authorization** (`src/webserver/auth/`)

   - **Purpose**: Manage user authentication, session management, and role-based access control
   - **Responsibilities**: Login/logout, JWT token generation, cookie-based sessions, RBAC middleware
   - **Domain Context**: `app-context/auth.md`
3. **Case File Management** (`src/process/database/`, `src/webserver/routes/caseRoutes.ts`)

   - **Purpose**: Organize legal cases with dedicated workspaces and document collections
   - **Responsibilities**: Case creation, workspace generation, case-document associations
   - **Domain Context**: `app-context/case-workspace-plan.md`
4. **Database Layer** (`src/process/database/`)

   - **Purpose**: Provide data persistence for users, cases, documents, conversations, and messages
   - **Responsibilities**: Schema management, migrations, CRUD operations, query execution
   - **Domain Context**: `app-context/data-model.md`
5. **WebUI Frontend** (`src/renderer/`)

   - **Purpose**: Provide browser-based user interface for all application features
   - **Responsibilities**: React components, routing, state management, API integration
   - **Standards**: `context-engine/standards/ui-components.md`
6. **Web Server** (`src/webserver/`)

   - **Purpose**: HTTP API server for frontend-backend communication
   - **Responsibilities**: REST endpoints, middleware, request handling, static file serving
   - **Standards**: `context-engine/standards/coding-patterns.md`

**Integration Points**:

- Frontend communicates with backend via REST API (Express routes)
- All API requests use cookie-based authentication (`aionui-session` cookie)
- Database accessed through repository pattern (synchronous operations)
- File storage accessed directly via Node.js `fs` module

**Shared Dependencies**:

- `better-sqlite3` - Database operations
- `express` - HTTP server
- `react` + `react-dom` - Frontend framework
- `@arco-design/web-react` - UI component library
- `jsonwebtoken` - JWT token generation/verification
- `bcrypt` - Password hashing

## Infrastructure & File Organization

### Base Workspace Structure

**Database Location**: `{userData}/config/aionui.db`

- macOS: `/Users/{username}/Library/Application Support/AionUi/aionui/config/aionui.db`
- Linux: `~/.config/AionUi/aionui/config/aionui.db`
- Windows: `%APPDATA%/AionUi/aionui/config/aionui.db`

**Case Workspace Base**: `~/.justicequest/`

- All case files are stored under this directory
- Each case gets a dedicated workspace folder

### Case Workspace Structure

When a case is created, a dedicated workspace is generated:

```
~/.justicequest/{case-name-timestamp}/
├── intake/                          # Temporary upload staging area
│   └── (files moved here during upload, then relocated to documents/)
├── documents/                       # Permanent document storage
│   └── {folder_name}/              # One folder per document
│       ├── original.{ext}          # Original uploaded file
│       ├── extracted-text.txt      # Extracted text from OCR/parsing
│       └── metadata.json           # AI-generated metadata
├── drafts/                         # Generated legal documents (future)
└── research/                       # Research materials (future)
```

**Naming Convention**: `{sanitized-case-title}-{timestamp}`

- Example: `smith-v-jones-1765622644973`
- Sanitization: Lowercase, replace non-alphanumeric with `-`, trim leading/trailing `-`

### Document Folder Structure

Each document gets its own folder named after the sanitized filename:

```
documents/
└── First_Amended_Complaint_____United_States_District_Court__Northern_District_of_Georgia_-_1.pdf/
    ├── original.pdf              # Original file (extension preserved)
    ├── extracted-text.txt        # Extracted text with page markers
    └── metadata.json             # AI analysis results
```

**Key Points**:

- `folder_name` is stored in the `case_documents` table
- Original file extension is preserved in `original.{ext}`
- All document artifacts are co-located in the same folder
- Deleting a document removes the entire folder

### Agent Instruction Files (`AGENTS.md` / `GEMINI.md`)

**Purpose**: These files act as the **"Brain"** or **Instruction Set** for the autonomous agent process (e.g., Gemini CLI, Auggie CLI) that operates within a specific case folder.

- **Location**: Located at the root of every case workspace (e.g., `~/.justicequest/{case-name-timestamp}/AGENTS.md`).
- **Origin**: Copied from `case-folder-template/` when a new case is created.
- **Function**:
  - Unlike `global-context.md` (which describes the *project*), `AGENTS.md` controls the **behavior** of the agent in that specific case.
  - It defines how the agent navigates, reads/writes files, and executes protocols within that workspace.
  - It provides the "identity" (e.g., "Ross AI") for the agent in that specific context.

**Critical Note for Coding Agents**:

- When you are asked to "update agent instructions," you are likely modifying `case-folder-template/AGENTS.md`.
- Understanding this distinction is vital: modifying the template changes the "brain" for all *future* cases (and potentially existing ones if synced).

### Tenant Data Isolation

**Single-Tenant Model**: Each deployment is completely isolated

- Separate database file per tenant
- Separate workspace directory per tenant
- No shared resources between tenants
- Each tenant requires independent infrastructure

**Multi-User Within Tenant**: Multiple users can access the same tenant's data

- Users share the same database and workspace
- Access control enforced via RBAC (roles: `super_admin`, `admin`, `user`)
- All users can see all cases (no user-level case isolation currently)

## Multi-User & Authentication

### User Roles

**Role Hierarchy**:

1. **`super_admin`** - Full system access, can manage all users and settings
2. **`admin`** - Can manage users and cases, limited system settings access
3. **`user`** - Can view and work with cases, no administrative privileges

### Authentication Flow

**Login Process**:

1. User submits username/password via `/login` endpoint
2. Backend verifies credentials using bcrypt (constant-time comparison)
3. JWT token generated and stored in `aionui-session` cookie
4. Cookie sent with all subsequent requests (`credentials: 'include'`)
5. `TokenMiddleware` extracts token from cookie and validates
6. User info attached to `req.user` for authorization checks

**Token Sources** (in priority order):

1. `aionui-session` cookie (primary method)
2. `Authorization: Bearer <token>` header (secondary)
3. `token` query parameter (fallback)

**Session Management**:

- JWT tokens expire after 7 days (configurable)
- Tokens stored in secure, httpOnly cookies
- No localStorage or sessionStorage used for tokens
- Token rotation available via `AuthService.invalidateAllTokens()`

### Authorization Patterns

**RBAC Middleware**: `requireRole(['admin', 'super_admin'])`

- Checks if authenticated user has required role
- Returns 401 if not authenticated
- Returns 403 if insufficient permissions

**Case Ownership**: Currently all users within a tenant can access all cases

- Future enhancement: Add user-level case ownership
- Would require `case_files.owner_id` column and ownership checks

## Knowledge Base & Onboarding Protocol

### Domain Context Files

**Location**: `context-engine/domain-contexts/`

**Purpose**: These files serve as the "institutional knowledge" for the codebase. They document:

- **Business Intent** - WHY things work the way they do
- **Code Navigation** - WHERE to find things, HOW to trace through code
- **Process Flows** - Step-by-step workflows and data transformations
- **Architectural Decisions** - Key design choices and their rationale

**When to Consult**:

- ✅ **ALWAYS** before making changes to an existing feature
- ✅ **ALWAYS** when uncertain about how a feature works
- ✅ **ALWAYS** before proposing architectural changes
- ✅ **ALWAYS** when onboarding to a new area of the codebase

**When to Update**:

- ✅ After implementing a new feature that requires extensive onboarding
- ✅ When discovering that documentation is outdated or inaccurate
- ✅ After making architectural changes that affect workflows
- ✅ When adding new integration points or dependencies

**Available Domain Contexts**:

- `document-intake-architecture.md` - Complete document processing pipeline
- (More to be added as features are implemented)

### Onboarding Protocol for Agents

**Step 1: Read Global Context** (this file)

- Understand architecture, deployment model, and core mission
- Review infrastructure and file organization
- Understand authentication and multi-user patterns

**Step 2: Identify Relevant Domain Context**

- Determine which feature area you're working in
- Load the corresponding domain context file(s)
- Read thoroughly before making any changes

**Step 3: Verify Current Implementation**

- Use `codebase-retrieval` to find relevant code
- Use `view` to read actual implementation
- Cross-reference with domain context documentation

**Step 4: Plan Changes**

- Consider impact on existing workflows
- Check for downstream dependencies
- Verify changes align with architectural decisions

**Step 5: Update Documentation**

- If implementation differs from docs, update docs first
- If adding new feature, create or update domain context
- Document any new architectural decisions

## Key Constraints & Guidelines

**Technical Constraints**:

- **WebUI-Only**: No Electron APIs or IPC bridge in new code
- **Synchronous Database**: All database operations must be synchronous (no async/await for DB calls)
- **Single-Tenant**: No multi-tenant features or shared resources
- **File-Based Storage**: Documents stored in filesystem, not database BLOBs
- **Cookie Authentication**: Primary auth method is `aionui-session` cookie, not Bearer tokens

**Business Constraints**:

- **Legal Confidentiality**: All data must remain isolated per tenant
- **Compliance**: Document retention and audit trails required
- **Performance**: Document processing must complete within reasonable time (< 5 minutes per document)

**Coding Standards**:

- See the `context-engine/standards/` directory for detailed coding standards
- **MANDATORY**: Consult standards before writing any code

## Architectural & Coding Standards

**Mandatory Adherence**: Before writing or modifying any code, you **MUST** consult the documents within the `context-engine/standards/` directory. These documents define the mandatory coding standards, design patterns, and architectural guidelines for this project.

**Standards Files**:

- `ui-components.md` - Reusable UI components (props, slots, usage patterns)
- `coding-patterns.md` - Backend patterns (error handling, typing, architecture)
- `reference-implementations.md` - Approved "Golden Samples" of correct implementations

**Rules**:

- ✅ **Adherence is not optional** - All code must follow documented standards
- ✅ **Check before coding** - Read relevant standards before starting work
- ✅ **Follow existing patterns** - If standard not defined, match existing codebase conventions
- ✅ **Update standards** - Document new patterns when creating reusable components
- ✅ **Standards are source of truth** - In case of conflict, standards override individual code examples

## Context Engineering Workflow

When assigned a new task, AI assistants should follow this workflow:

### 1. **Read Global Context** (this file)

- Understand the architecture, deployment model, and core mission
- Review infrastructure and file organization
- Understand authentication and multi-user patterns
- Check key constraints and guidelines

### 2. **Consult Domain Context**

- Identify which feature area the task involves
- Load relevant domain context file(s) from `context-engine/domain-contexts/`
- Read thoroughly to understand existing workflows and patterns
- **CRITICAL**: Do NOT skip this step. Domain contexts prevent breaking existing functionality.

### 3. **Review Coding Standards**

- Check `context-engine/standards/` for relevant patterns
- Review UI components if working on frontend
- Review coding patterns if working on backend
- Check reference implementations for similar features

### 4. **Gather Implementation Details**

- Use `codebase-retrieval` to find relevant code sections
- Use `view` to read actual implementation files
- Cross-reference code with domain context documentation
- Verify current implementation matches documentation (update docs if not)

### 5. **Plan Changes**

- Use task management tools for complex work
- Break down into atomic, testable units
- Consider impact on existing workflows
- Check for downstream dependencies
- Verify changes align with architectural decisions

### 6. **Implement Changes**

- Follow coding standards strictly
- Make minimal, surgical changes
- Respect existing patterns and conventions
- Update tests for affected code
- Document any new patterns or components

### 7. **Update Documentation**

- If implementation differs from docs, update docs
- If adding new feature requiring onboarding, update or create domain context
- Document architectural decisions in decision log
- Update standards if creating reusable patterns

### 8. **Suggest Testing**

- Always recommend writing or updating tests
- Suggest running existing tests to verify no regressions
- Provide specific test scenarios based on changes made

## Available Domain Contexts

**Current Domain Contexts** (in `context-engine/domain-contexts/`):

1. **`document-intake-architecture.md`**
   - Complete document processing pipeline (upload → extract → analyze → index)
   - File storage structure and paths
   - API endpoints and authentication
   - UI component behavior
   - Processing status workflow

**Future Domain Contexts** (to be created as features are implemented):

- Legal document generation workflows
- Case management and organization
- User management and RBAC
- AI agent integration patterns
- Research and citation management

**When to Create New Domain Context**:

- Feature requires extensive onboarding (> 30 minutes to understand)
- Multiple files and workflows involved
- Complex business logic or state machines
- Integration with external services
- Architectural patterns that should be reused

## Decision History

### 2025-12-13: WebUI-Only Architecture

**Decision**: Deprecate Electron desktop app, run exclusively in WebUI mode
**Rationale**: Simplifies deployment, reduces maintenance, enables easier updates
**Impact**: No IPC bridge or Electron APIs in new code. All features must work in browser.

### 2025-12-13: Single-Tenant Model

**Decision**: One firm = one tenant, dedicated infrastructure per tenant
**Rationale**: Legal data requires strict isolation for confidentiality and compliance
**Impact**: No shared resources between tenants. Each deployment is independent.

### 2025-12-13: Cookie-Based Authentication

**Decision**: Use `aionui-session` cookie as primary authentication method
**Rationale**: More secure than localStorage, works seamlessly with WebUI, prevents XSS token theft
**Impact**: All API calls use `credentials: 'include'`. No Bearer tokens in localStorage.

### 2025-12-13: File-Based Document Storage

**Decision**: Store documents at `documents/{folder_name}/original.{ext}` instead of database BLOBs
**Rationale**: Keeps database lightweight, enables direct file access, simplifies backup/restore
**Impact**: Document paths tracked in database. File operations require filesystem access.

### 2025-12-13: Synchronous Database Operations

**Decision**: Use SQLite with synchronous operations (better-sqlite3)
**Rationale**: Single-tenant model doesn't require distributed database. Simplifies code.
**Impact**: All database operations are synchronous. Migration to async DB would require major refactor.

## Notes & Updates

**Last Updated**: 2025-12-13
**Updated By**: AI Assistant (Augment Agent)
**Changes**:

- Complete rewrite of global context to reflect actual AionUi implementation
- Added architecture and deployment model documentation
- Added infrastructure and file organization details
- Added multi-user and authentication patterns
- Added knowledge base and onboarding protocol
- Added decision history with key architectural decisions
- Documented core mission and purpose as agentic legal framework

---

## Critical Reminders for AI Agents

### Before Making ANY Changes

1. ✅ **Read this global context** - Understand architecture and constraints
2. ✅ **Consult domain context** - Load relevant domain context file(s)
3. ✅ **Review coding standards** - Check `context-engine/standards/`
4. ✅ **Verify current implementation** - Use `codebase-retrieval` and `view`
5. ✅ **Plan before coding** - Use task management for complex work

### Architecture Constraints (DO NOT VIOLATE)

- ❌ **NO Electron APIs** - WebUI-only, no IPC bridge
- ❌ **NO async database calls** - SQLite is synchronous only
- ❌ **NO multi-tenant features** - Single-tenant architecture
- ❌ **NO localStorage auth** - Cookie-based authentication only
- ❌ **NO database BLOBs for documents** - File-based storage only

### When Uncertain

- 🔍 **Check domain context first** - Don't guess, read the docs
- 🔍 **Ask user if unclear** - Better to ask than break existing functionality
- 🔍 **Search codebase** - Use `codebase-retrieval` to find similar patterns
- 🔍 **Verify with view** - Read actual implementation before changing

### After Making Changes

- ✅ **Update documentation** - Keep domain contexts accurate
- ✅ **Suggest tests** - Always recommend testing changes
- ✅ **Document decisions** - Add to decision history if architectural
- ✅ **Update standards** - Document new reusable patterns

---

## Universal Guidelines

- Always include explicit acceptance criteria for tasks
- Document architectural decisions in decision history
- Consider forward compatibility and technical debt
- Update context documents when making architectural changes
- Use task management tools for complex multi-step work
- Suggest writing/updating tests after code changes
- Make minimal, surgical changes - respect existing patterns
- When in doubt, consult domain context or ask user
