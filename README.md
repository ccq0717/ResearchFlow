# ResearchFlow

ResearchFlow is an evidence-first AI research workspace that turns an open-ended research goal into a traceable plan, gathers information from the web, academic sources, and a private knowledge base, and produces a structured report with verifiable citations.

The initial demonstration scenario is researching evaluation methods for AI code-generation tools and producing an actionable evaluation plan.

## Current milestone

The repository currently contains a runnable simulated vertical slice:

- create a research run from the Next.js Dashboard;
- persist runs and events in SQLite;
- stream workflow progress with Server-Sent Events;
- display planning, retrieval, analysis, writing, and finalization stages;
- reopen completed work from research history;
- generate a placeholder Markdown report without calling an external model.

Real LLM, academic search, web retrieval, evidence extraction, RAG, and citation validation will be added in later milestones.

## Stack

- Next.js 16, React 19, TypeScript, Tailwind CSS
- FastAPI, Python 3.12, SQLAlchemy
- SQLite for the local MVP
- REST and Server-Sent Events
- LangGraph planned behind a ResearchFlow-owned workflow interface

## Repository layout

    apps/web       Next.js frontend
    apps/api       FastAPI backend
    docs           Product, architecture, decisions, and research notes
    examples       Public demonstration inputs
    infra          Optional deployment configuration
    scripts        Local development helpers
    var            Local runtime data (not committed)

Start with the [MVP specification](docs/product/mvp-spec.md), [domain model](docs/architecture/domain-model.md), [SSE contract](docs/architecture/sse-events.md), and [repository structure](docs/architecture/repository-structure.md).

## Prerequisites

- Windows 10 or 11
- Git
- Node.js 20.9 or newer
- npm
- uv

Docker, Redis, a GPU, and a local LLM are not required.

## Setup

From the repository root:

    uv sync --package researchflow-api
    Copy-Item .env.example .env
    npm install --prefix apps/web

The Python environment is created at .venv. Runtime data is created under var/.

## Run locally

Open two PowerShell terminals from the repository root.

Backend:

    .\.venv\Scripts\python.exe -m uvicorn researchflow.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 --reload

Frontend:

    Set-Location apps/web
    npm run dev

Open [http://localhost:3000](http://localhost:3000). FastAPI health is available at [http://localhost:8000/health](http://localhost:8000/health), and interactive API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

## Verify

Backend:

    .\.venv\Scripts\python.exe -m pytest apps/api/tests -q
    .\.venv\Scripts\ruff.exe check apps/api

Frontend:

    Set-Location apps/web
    npm run lint
    npm run build

## Configuration and security

Copy .env.example to .env for local configuration. Never commit API keys, private research documents, local databases, uploads, indexes, or generated reports. Local secrets and runtime files are ignored by Git.

## Project documentation

- [Project discussion](docs/product/project-discussion.md)
- [Hello-Agents reference analysis](docs/research/hello-agents-analysis.md)
- [LangGraph architecture decision](docs/decisions/0001-use-langgraph-behind-workflow-interface.md)
