from typing import Any, Dict

from langchain_core.messages import AIMessage

from ...classes import ResearchState
from .base import BaseResearcher

class IndustryAnalyzer(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()
        self.analyst_type = "industry_analyzer"

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', 'Unknown Industry')
        msg = [f"🏭 Industry Analyzer analyzing {company} in {industry}"]

        # Expanded: Generate broader industry research queries
        queries = await self.generate_queries(state, f"""
        Generate queries on the industry analysis of {company} in the {industry} industry such as:
        - Market position
        - Competitors
        - {industry} industry trends and challenges
        - Market size and growth
        - Regulatory environment and compliance
        - Supply chain and logistics
        - Technology and innovation trends
        - Customer segments and behavior
        - Sustainability and ESG (Environmental, Social, Governance) factors
        - Financial benchmarks and industry averages
        """)

        subqueries_msg = "🔍 Subqueries for industry analysis:\n" + "\n".join([f"• {query}" for query in queries])
        messages = state.get('messages', [])
        messages.append(AIMessage(content=subqueries_msg))
        state['messages'] = messages

        # Send queries through WebSocket
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Industry analysis queries generated",
                    result={
                        "step": "Industry Analyst",
                        "analyst_type": "Industry Analyst",
                        "queries": queries
                    }
                )

        industry_data = {}

        # Include site scrape data if available
        if site_scrape := state.get('site_scrape'):
            msg.append("\n📊 Including site scrape data in industry analysis...")
            company_url = state.get('company_url', 'company-website')
            industry_data[company_url] = {
                'title': state.get('company', 'Unknown Company'),
                'raw_content': site_scrape,
                'query': f'Industry analysis on {company}'
            }

        # Expanded: Integrate additional data sources (pseudo-code for illustration)
        # Example: Fetch real-time market data, regulatory filings, or news
        # real_time_data = await self.fetch_real_time_market_data(industry)
        # if real_time_data:
        #     industry_data['real_time_market'] = real_time_data

        # Perform additional research with increased search depth
        try:
            for query in queries:
                documents = await self.search_documents(state, [query])
                if documents:
                    for url, doc in documents.items():
                        doc['query'] = query
                        industry_data[url] = doc

            msg.append(f"\n✓ Found {len(industry_data)} documents")
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message=f"Used Tavily Search to find {len(industry_data)} documents",
                        result={
                            "step": "Searching",
                            "analyst_type": "Industry Analyst",
                            "queries": queries
                        }
                    )
        except Exception as e:
            msg.append(f"\n⚠️ Error during research: {str(e)}")

        # Expanded: Structure output for richer reporting
        structured_report = {
            "Market Position": [],
            "Competitors": [],
            "Trends and Challenges": [],
            "Market Size and Growth": [],
            "Regulatory Environment": [],
            "Supply Chain": [],
            "Technology and Innovation": [],
            "Customer Segments": [],
            "Sustainability and ESG": [],
            "Financial Benchmarks": [],
            "Other": []
        }
        for url, doc in industry_data.items():
            query = doc.get('query', '').lower()
            if "market position" in query:
                structured_report["Market Position"].append(doc)
            elif "competitor" in query:
                structured_report["Competitors"].append(doc)
            elif "trend" in query or "challenge" in query:
                structured_report["Trends and Challenges"].append(doc)
            elif "market size" in query or "growth" in query:
                structured_report["Market Size and Growth"].append(doc)
            elif "regulatory" in query or "compliance" in query:
                structured_report["Regulatory Environment"].append(doc)
            elif "supply chain" in query or "logistics" in query:
                structured_report["Supply Chain"].append(doc)
            elif "technology" in query or "innovation" in query:
                structured_report["Technology and Innovation"].append(doc)
            elif "customer" in query or "segment" in query:
                structured_report["Customer Segments"].append(doc)
            elif "sustainability" in query or "esg" in query:
                structured_report["Sustainability and ESG"].append(doc)
            elif "financial" in query or "benchmark" in query or "average" in query:
                structured_report["Financial Benchmarks"].append(doc)
            else:
                structured_report["Other"].append(doc)

        # Update state with findings and structured report
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['industry_data'] = industry_data
        state['industry_report'] = structured_report

        return {
            'message': msg,
            'industry_data': industry_data,
            'industry_report': structured_report
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state)
