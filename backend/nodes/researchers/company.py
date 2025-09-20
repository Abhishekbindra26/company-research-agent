from typing import Any, Dict
from langchain_core.messages import AIMessage

from ...classes import ResearchState
from .base import BaseResearcher

import os
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio
import re
import logging

class CompanyAnalyzer(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()
        self.analyst_type = "company_analyzer"
        self._configure_gemini()

    def _configure_gemini(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env file.")
        genai.configure(api_key=api_key)

    async def get_employee_count_via_llm(self, company: str, industry: str = None) -> str:
        """
        Enhanced employee count retrieval with better error handling and validation.
        """
        prompt = (
            "You are a business data analyst. Your job is to provide the most recent employee count for a company.\n"
            "- If you know the number, respond with only the number (no words, no formatting, no commas).\n"
            "- If you do not know, respond with your best approximation based on company size and industry.\n"
            "- If you know the year, append it in parentheses, e.g., 1200 (2023).\n"
            "- For small companies or startups, estimate between 10-100.\n"
            "- For medium companies, estimate between 100-1000.\n"
            "- For large corporations, estimate between 1000-100000+.\n"
            "\n"
            "Examples:\n"
            "Q: What is the most recent employee count for 'Google'?\n"
            "A: 182502 (2023)\n"
            "\n"
            "Q: What is the most recent employee count for 'Acme Widgets'?\n"
            "A: 150\n"
            "\n"
            "Q: What is the most recent employee count for 'Tesla'?\n"
            "A: 140473 (2023)\n"
            "\n"
            f"Now answer:\nQ: What is the most recent employee count for '{company}'"
            + (f" in the {industry} industry" if industry else "")
            + "?\nA:"
        )

        try:
            def call_gemini():
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text.strip()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, call_gemini)
            
            # Enhanced parsing to extract employee count
            match = re.search(r"(\d[\d,]*)", result)
            if match:
                clean_count = match.group(1).replace(",", "")
                logging.info(f"Successfully extracted employee count duriing api call in company.py: {clean_count} for {company}")
                return clean_count
            else:
                logging.warning(f"Could not parse employee count from Gemini response: {result}")
                return "1"  # Default fallback
                
        except Exception as e:
            logging.error(f"Error getting employee count from Gemini for {company}: {e}")
            return "1"  # Fallback value

    def _validate_and_process_employee_count(self, raw_count: str, company: str) -> int:
        """
        Validates and processes the raw employee count string into a clean integer.
        """
        try:
            # Remove any non-digit characters except for parentheses content
            clean_count = re.sub(r'[^\d]', '', raw_count.split('(')[0].strip())
            
            if clean_count:
                employee_count = int(clean_count)
                # Validate reasonable range (1 to 10 million employees)
                if 1 <= employee_count <= 10000000:
                    logging.info(f"Valid employee count processed: {employee_count} for {company}")
                    return employee_count
                else:
                    logging.warning(f"Employee count {employee_count} outside reasonable range for {company}")
                    return 1  # Default fallback
            else:
                logging.warning(f"No digits found in employee count '{raw_count}' for {company}")
                return 1
                
        except (ValueError, TypeError) as e:
            logging.error(f"Failed to process employee count '{raw_count}' for {company}: {e}")
            return 1

    async def _send_employee_count_update(self, state: ResearchState, employee_count: int, company: str):
        """
        Sends immediate WebSocket update with employee count data for UI.
        """
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')
        
        if websocket_manager and job_id:
            try:
                # Get current enrichment counts and update with employee count
                current_enrichment_counts = state.get('enrichment_counts', {})
                
                # Update employee count in enrichment counts
                current_enrichment_counts['employeeCount'] = {
                    "enriched": employee_count,
                    "total": 1,
                    "data": {company: employee_count},
                    "hasData": employee_count > 0
                }
                
                # Update state with new enrichment counts
                state['enrichment_counts'] = current_enrichment_counts
                
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="employee_count_ready",
                    message=f"Employee count determined: {employee_count:,}",
                    result={
                        "step": "Employee Count Analysis",
                        "analyst_type": "Company Analyst",
                        "enrichmentCounts": current_enrichment_counts,
                        "employee_count": state.get('employee_count', {}),
                        "company_count": state.get('Company_Count', 0),
                        "employee_data": {
                            "company": company,
                            "count": employee_count,
                            "formatted": f"{employee_count:,}"
                        }
                    }
                )
                logging.info(f"Sent employee count WebSocket update: {employee_count} for {company}")
            except Exception as e:
                logging.error(f"Error sending employee count WebSocket update: {e}")

    async def _send_enrichment_counts_update(self, state: ResearchState):
        """
        Sends updated enrichment counts to UI including all categories.
        """
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')
        
        if websocket_manager and job_id:
            try:
                # Build comprehensive enrichment counts
                enrichment_counts = {
                    "company": {
                        "enriched": len(state.get('company_data', {})),
                        "total": state.get('Company_Count', 0) + len(state.get('company_data', {}))
                    },
                    "employeeCount": {
                        "enriched": next(iter(state.get('employee_count', {None: 0}).values())),
                        "total": 1
                    },
                    "industry": {
                        "enriched": len(state.get('industry_data', {})),
                        "total": len(state.get('industry_data', {}))
                    },
                    "financial": {
                        "enriched": len(state.get('financial_data', {})),
                        "total": len(state.get('financial_data', {}))
                    },
                    "news": {
                        "enriched": len(state.get('news_data', {})),
                        "total": len(state.get('news_data', {}))
                    }
                }
                
                state['enrichment_counts'] = enrichment_counts
                
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="enrichment_counts_updated",
                    message="Enrichment counts updated",
                    result={
                        "step": "Enrichment Counts Update",
                        "analyst_type": "Company Analyst",
                        "enrichmentCounts": enrichment_counts
                    }
                )
                
            except Exception as e:
                logging.error(f"Error sending enrichment counts update: {e}")

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', None)
        msg = [f"🏢 Company Analyzer analyzing {company}"]

        # Generate analysis queries
        queries = await self.generate_queries(state, f"""
        Generate queries on the company fundamentals of {company} in the {industry or 'unknown'} industry such as:
        - Core products and services
        - Company history and milestones
        - Leadership team and key personnel, dont forget to include CTO and CEO
        - Business model and strategy
        - Market position and competitive advantages
        - Recent developments and news
        """)

        subqueries_msg = "🔍 Subqueries for company analysis:\n" + "\n".join([f"• {query}" for query in queries])
        messages = state.get('messages', [])
        messages.append(AIMessage(content=subqueries_msg))
        state['messages'] = messages

        # Send initial WebSocket update
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')
        if websocket_manager and job_id:
            await websocket_manager.send_status_update(
                job_id=job_id,
                status="processing",
                message="Company analysis queries generated",
                result={
                    "step": "Company Analyst",
                    "analyst_type": "Company Analyst",
                    "queries": queries,
                    "query_count": len(queries)
                }
            )

        company_data = {}

        # Add site scrape data if available
        site_scrape = state.get('site_scrape')
        if site_scrape:
            company_url = state.get('company_url', 'company-website')
            msg.append("\n📊 Including site scrape data in company analysis...")
            company_data[company_url] = {
                'title': company,
                'raw_content': site_scrape,
                'query': f'Company overview and information about {company}'
            }

        # Enhanced employee count extraction - MOVED TO BEGINNING FOR IMMEDIATE UI UPDATE
        try:
            msg.append(f"\n👥 Analyzing employee count for {company}...")
            
            # Send loading state update for employee count
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Analyzing employee count...",
                    result={
                        "step": "Employee Count Analysis",
                        "analyst_type": "Company Analyst",
                        "enrichmentCounts": {
                            "employeeCount": {
                                "enriched": 0,
                                "total": 1,
                                "loading": True
                            }
                        }
                    }
                )
            
            employee_count_raw = await self.get_employee_count_via_llm(company, industry)
            employee_count_value = self._validate_and_process_employee_count(employee_count_raw, company)
            
            msg.append(f"👥 Employee count determined: {employee_count_value:,}")
            logging.info(f"Processed employee count in company.py for {company}: {employee_count_value}")
            print("\n"*10)
            # Determine company URL/key for data storage
            company_url = state.get('company_url', company.lower().replace(' ', '-'))
            
            # Update state with employee count information IMMEDIATELY
            if 'employee_count' not in state:
                state['employee_count'] = {}
            state['employee_count'][company_url] = employee_count_value
            state['Company_Count'] = 1 if employee_count_value > 0 else 0
            
            # Send immediate employee count update via WebSocket
            await self._send_employee_count_update(state, employee_count_value, company)
            
            # Update enrichment counts
            await self._send_enrichment_counts_update(state)
            
        except Exception as e:
            logging.error(f"Error during employee count analysis for {company}: {e}")
            employee_count_value = 100
            msg.append(f"⚠️ Using fallback employee count: {employee_count_value}")
            
            # Still update state with fallback value
            company_url = state.get('company_url', company.lower().replace(' ', '-'))
            if 'employee_count' not in state:
                state['employee_count'] = {}
            state['employee_count'][company_url] = employee_count_value
            state['Company_Count'] = 1
            
            # Send fallback update
            await self._send_employee_count_update(state, employee_count_value, company)

        # Ensure the main company entry exists and update with employee count
        if company_url not in company_data:
            company_data[company_url] = {
                'title': company,
                'raw_content': site_scrape or "",
                'query': f'Company overview and information about {company}'
            }
        
        # Add employee count to company data
        company_data[company_url]['employee_count'] = employee_count_value

        # Search for additional company documents
        try:
            msg.append(f"\n🔍 Searching for additional company documents...")
            
            for i, query in enumerate(queries):
                try:
                    documents = await self.search_documents(state, [query])
                    if documents:
                        for url, doc in documents.items():
                            doc['query'] = query
                            doc['query_index'] = i
                            company_data[url] = doc
                        msg.append(f"  ✓ Query {i+1}: Found {len(documents)} documents")
                    else:
                        msg.append(f"  • Query {i+1}: No documents found")
                        
                except Exception as e:
                    logging.error(f"Error searching for query '{query}': {e}")
                    msg.append(f"  ⚠️ Query {i+1}: Search error")

            msg.append(f"\n✅ Company analysis complete: {len(company_data)} total documents")
            
            # Send final comprehensive WebSocket update
            if websocket_manager and job_id:
                # Final enrichment counts update
                await self._send_enrichment_counts_update(state)
                
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="company_analysis_complete",
                    message=f"Company analysis complete. Found {len(company_data)} documents",
                    result={
                        "step": "Company Analysis Complete",
                        "analyst_type": "Company Analyst",
                        "queries": queries,
                        "employee_count": state.get('employee_count', {}),
                        "company_count": state.get('Company_Count', 0),
                        "documents_found": len(company_data),
                        "enrichmentCounts": state.get('enrichment_counts', {}),
                        "employee_data": {
                            "company": company,
                            "count": employee_count_value,
                            "formatted": f"{employee_count_value:,}",
                            "source": "Gemini AI Analysis"
                        }
                    }
                )
                
        except Exception as e:
            msg.append(f"\n⚠️ Error during document search: {str(e)}")
            logging.error(f"Error during company document search: {e}")

        # Update messages with final status
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['company_data'] = company_data
        
        # Log final state for debugging
        logging.info(f"Company analysis complete for {company}")
        logging.info(f"Final employee count: {state.get('employee_count')}")
        logging.info(f"Company_Count: {state.get('Company_Count')}")
        logging.info(f"Total documents found: {len(company_data)}")
        logging.info("\n"*10)
        return {
            'messages': messages,
            'company_data': company_data,
            'employee_count': state.get('employee_count', {}),
            'Company_Count': state.get('Company_Count', 0),
            'enrichment_counts': state.get('enrichment_counts', {})
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        """
        Main entry point for the company analyzer.
        """
        try:
            return await self.analyze(state)
        except Exception as e:
            logging.error(f"Critical error in CompanyAnalyzer.run: {e}")
            # Return minimal state to prevent pipeline failure
            return {
                'messages': state.get('messages', []),
                'company_data': {},
                'employee_count': {},
                'Company_Count': 0,
                'enrichment_counts': {}
            }

