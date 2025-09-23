 [![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/pogjester/company-research-agent/blob/main/README.md)
[![zh](https://img.shields.io/badge/lang-zh-green.svg)](https://github.com/pogjester/company-research-agent/blob/main/README.zh.md)
[![fr](https://img.shields.io/badge/lang-fr-blue.svg)](https://github.com/pogjester/company-research-agent/blob/main/README.fr.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/pogjester/company-research-agent/blob/main/README.es.md)
[![jp](https://img.shields.io/badge/lang-jp-orange.svg)](https://github.com/pogjester/company-research-agent/blob/main/README.jp.md)
[![kr](https://img.shields.io/badge/lang-ko-purple.svg)](https://github.com/pogjester/company-research-agent/blob/main/README.kr.md)


# Agentic Company Researcher 🔍

![web ui](<static/ui-1.png>)

A multi-agent tool that generates comprehensive company research reports. The platform uses a pipeline of AI agents to gather, curate, and synthesize information about any company.


https://github.com/user-attachments/assets/0e373146-26a7-4391-b973-224ded3182a9

## Features

- **Multi-Source Research**: Gathers data from various sources including company websites, news articles, financial reports, and industry analyses
- **AI-Powered Content Filtering**: Uses Tavily's relevance scoring for content curation
- **Real-Time Progress Streaming**: Uses WebSocket connections to stream research progress and results
- **Dual Model Architecture**:
  - Gemini 2.0 Flash for high-context research synthesis
  - GPT-4.1 for precise report formatting and editing
- **Modern React Frontend**: Responsive UI with real-time updates, progress tracking, and download options
- **Modular Architecture**: Built using a pipeline of specialized research and processing nodes

## Agent Framework

### Research Pipeline

The platform follows an agentic framework with specialized nodes that process data sequentially:

1. **Research Nodes**:
   - `CompanyAnalyzer`: Researches core business information
   - `IndustryAnalyzer`: Analyzes market position and trends
   - `FinancialAnalyst`: Gathers financial metrics and performance data
   - `NewsScanner`: Collects recent news and developments

2. **Processing Nodes**:
   - `Collector`: Aggregates research data from all analyzers
   - `Curator`: Implements content filtering and relevance scoring
   - `Briefing`: Generates category-specific summaries using Gemini 2.0 Flash
   - `Editor`: Compiles and formats the briefings into a final report using GPT-4.1-mini

   ![web ui](<static/agent-flow.png>)

### Content Generation Architecture

The platform leverages separate models for optimal performance:

1. **Gemini 2.0 Flash** (`briefing.py`):
   - Handles high-context research synthesis tasks
   - Excels at processing and summarizing large volumes of data
   - Used for generating initial category briefings
   - Efficient at maintaining context across multiple documents

2. **GPT-4.1 mini (`editor.py`)**:
   - Handles formatting, deduplication, and markdown structure.
   - Provides real-time report generation with clean outputs.

### Content Filtering

The relevance scoring system helps ensure that only the most pertinent documents are included:

- Documents are scored based on their relevance to the query.
- Scores below a defined threshold are excluded.
- URLs are deduplicated, and documents are normalized for consistency.
- Real-time updates keep users informed throughout the research process.

### Real-Time Communication System

The platform implements a WebSocket-based real-time communication system:

![web ui](<static/ui-2.png>)

1. **Backend Implementation**:
   - Uses FastAPI's WebSocket support
   - Maintains persistent connections per research job
   - Sends structured status updates for various events:
     ```python
     await websocket_manager.send_status_update(
         job_id=job_id,
         status="processing",
         message=f"Generating {category} briefing",
         result={
             "step": "Briefing",
             "category": category,
             "total_docs": len(docs)
         }
     )
     ```

2. **Frontend Integration**:
   - React components subscribe to WebSocket updates
   - Updates are processed and displayed in real-time
   - Different UI components handle specific update types:
     - Query generation progress
     - Document curation statistics
     - Briefing completion status
     - Report generation progress

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
