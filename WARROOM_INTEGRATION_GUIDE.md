# War Room Researcher Integration Guide

## Overview

**War Room Researcher** is a customized fork of GPT Researcher optimized for legal research workflows. It includes:

- **Scrape Bypass Mode**: Skips RAG compression and writes raw scraped files to disk for inspection
- **Case Documents Parameter**: Integrates legal documents into the research workflow
- **Curation Pipeline**: Designed to work with Auggie/Gemini CLI for intelligent curation
- **Legal Research Optimizations**: Tailored for motion analysis, case law research, and legal precedent discovery

---

## Docker Image Location

```
ghcr.io/ianbrucey/war-room-researcher:latest
ghcr.io/ianbrucey/war-room-researcher:v1.0.0
```

**Repository**: https://github.com/ianbrucey/war-room-researcher

---

## Integration with War Room

### Option 1: Multi-Container Setup (Recommended)

Add War Room Researcher as a separate service in your `docker-compose.yml`:

```yaml
services:
  war-room:
    build: .
    container_name: war-room
    depends_on:
      - war-room-researcher
    ports:
      - "80:25808"
    volumes:
      - war-room-data:/root/.config/AionUi
      - case-workspace-data:/root/.justicequest
      - research-output:/tmp/research_output:ro  # Shared volume (read-only)
      - ./docker-auth/augment:/root/.augment
      - ./docker-auth/gemini:/root/.gemini
      - ./docker-auth/legal-hub/.env:/opt/legal-hub/mcp-server/.env
    env_file:
      - .env
    environment:
      - PORT=25808
      - NODE_ENV=production
      - DISPLAY=:99
      - WAR_ROOM_RESEARCHER_URL=http://war-room-researcher:8000
    restart: unless-stopped

  war-room-researcher:
    image: ghcr.io/ianbrucey/war-room-researcher:latest
    container_name: war-room-researcher
    ports:
      - "8000"  # Internal only
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - SKIP_EMBEDDING_COMPRESSION=true
      - SCRAPE_OUTPUT_DIR=/tmp/research_output
    volumes:
      - research-output:/tmp/research_output  # Shared volume (write access)
    restart: unless-stopped

volumes:
  war-room-data:
  case-workspace-data:
  research-output:  # New volume for scraped files
```

---

## Environment Variables

### Required API Keys
- `OPENAI_API_KEY` - OpenAI API key for LLM calls
- `TAVILY_API_KEY` - Tavily API key for web search

### Optional Configuration
- `LANGCHAIN_API_KEY` - LangChain tracing (optional)
- `SKIP_EMBEDDING_COMPRESSION` - Set to `true` to enable bypass mode (default: `true`)
- `SCRAPE_OUTPUT_DIR` - Custom directory for scraped files (default: `/tmp/research_output`)

---

## API Usage

### HTTP Endpoint

```bash
POST http://war-room-researcher:8000/report/
Content-Type: application/json

{
  "task": "What are the key precedents for motion to dismiss in federal court?",
  "report_type": "research_report",
  "report_source": "web",
  "tone": "Objective",
  "generate_in_background": false
}
```

### Response

```json
{
  "report": "# Research Report\n\n...",
  "research_id": "research_abc123",
  "scraped_dir": "/tmp/research_output/research_abc123/scraped"
}
```

---

## Workflow: Scrape → Curate → Synthesize

### Step 1: Run Research (Scraping)

```bash
curl -X POST http://war-room-researcher:8000/report/ \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Legal research query",
    "report_type": "research_report",
    "report_source": "web"
  }'
```

This writes raw scraped files to `/tmp/research_output/research_*/scraped/`

### Step 2: Curate with Auggie/Gemini

```bash
# From War Room container
auggie -p "Analyze the files in /tmp/research_output/research_*/scraped/ and produce a curated summary..."
```

### Step 3: Synthesize Final Report

```bash
# Use curated output to generate final report
auggie -p "Using the curated summary, draft a legal memo..."
```

---

## Deployment Script Updates

Update `scripts/deploy-client.sh` to pull the War Room Researcher image:

```bash
# In the remote execution section, add:
echo "⬇️  Pulling War Room Researcher image..."
docker pull ghcr.io/ianbrucey/war-room-researcher:latest

# Start services
docker compose up -d --no-build
```

---

## Testing the Integration

```bash
# 1. Start services
docker compose up -d

# 2. Test the API
curl -X POST http://localhost:8000/report/ \
  -H "Content-Type: application/json" \
  -d '{"task": "test query", "report_type": "research_report", "report_source": "web"}'

# 3. Check scraped files
docker exec war-room-researcher ls -lah /tmp/research_output/

# 4. Access from War Room container
docker exec war-room ls -lah /tmp/research_output/
```

---

## Next Steps

1. **Update docker-compose.yml** - Add war-room-researcher service
2. **Update .env** - Add required API keys
3. **Update deploy-client.sh** - Add image pull command
4. **Test locally** - `docker compose up -d` and verify communication
5. **Deploy** - Use existing deployment workflow

---

## Support

- **Repository**: https://github.com/ianbrucey/war-room-researcher
- **Issues**: https://github.com/ianbrucey/war-room-researcher/issues

