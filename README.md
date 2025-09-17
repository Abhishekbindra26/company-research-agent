[![en](https://img.shields.io/badge/lang-en-red.svg)]()
[![zh](https://img.shields.io/badge/lang-zh-green.svg)]()
[![fr](https://img.shields.io/badge/lang-fr-blue.svg)]()
[![es](https://img.shields.io/badge/lang-es-yellow.svg)]()
[![jp](https://img.shields.io/badge/lang-jp-orange.svg)]()
[![kr](https://img.shields.io/badge/lang-ko-purple.svg)]()

# My Agentic Company Research Tool 🔍

![web ui](<static/ui-1.png>)

This is a personal project where I’ve built a multi-agent platform that generates detailed research reports on companies. It leverages a pipeline of AI agents to gather, filter, and present information from various sources, providing users with structured and insightful company reports.

## Key Features

- **Multi-Source Research**: Collects information from company websites, news outlets, financial reports, and industry data.
- **AI-Powered Content Filtering**: Uses relevance scoring to ensure curated and high-quality content.
- **Real-Time Streaming**: Research progress and results are streamed live using WebSocket connections.
- **Dual AI Architecture**:
  - Gemini 2.0 Flash for deep research synthesis
  - GPT-4.1 for report formatting and editing
- **Modern React Frontend**: Clean, responsive UI with real-time updates and download options.
- **Modular and Scalable**: Built as a pipeline of independent, reusable components.

## How It Works

### Research Pipeline

I’ve structured the platform using an agent-based pipeline where each node is responsible for a specific part of the research and report generation:

1. **Research Nodes**:
   - `CompanyAnalyzer`: Finds core business details.
   - `IndustryAnalyzer`: Evaluates market position and trends.
   - `FinancialAnalyst`: Gathers financial data and metrics.
   - `NewsScanner`: Collects recent news and developments.

2. **Processing Nodes**:
   - `Collector`: Aggregates data from all research agents.
   - `Curator`: Filters and prioritizes content.
   - `Briefing`: Summarizes content into key sections using Gemini 2.0 Flash.
   - `Editor`: Polishes the final report using GPT-4.1-mini.

![pipeline diagram](<static/agent-flow.png>)

### AI Models Used

1. **Gemini 2.0 Flash (`briefing.py`)**:
   - Processes and summarizes large datasets.
   - Keeps context across multiple documents.
   - Generates initial summaries.

2. **GPT-4.1 mini (`editor.py`)**:
   - Handles formatting, deduplication, and markdown structure.
   - Provides real-time report generation with clean outputs.

### Content Filtering

The relevance scoring system helps ensure that only the most pertinent documents are included:

- Documents are scored based on their relevance to the query.
- Scores below a defined threshold are excluded.
- URLs are deduplicated, and documents are normalized for consistency.
- Real-time updates keep users informed throughout the research process.

### Real-Time Communication

The project implements WebSocket for real-time updates between the backend and frontend:

1. **Backend**:
   - Built with FastAPI’s WebSocket support.
   - Sends structured status updates for each step.

2. **Frontend**:
   - Subscribes to live updates.
   - Displays progress, document stats, and report generation in real time.

3. **Status Types**:
   - Query creation
   - Document filtering
   - Briefing start/completion
   - Report generation updates

## Setup Instructions

### Quick Setup

1. Clone the project:
   ```bash
   git clone https://github.com/your-username/my-company-research.git
   cd my-company-research
