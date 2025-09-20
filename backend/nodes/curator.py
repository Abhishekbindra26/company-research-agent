import logging
from typing import Dict
from urllib.parse import urljoin, urlparse

from langchain_core.messages import AIMessage

from ..classes import ResearchState
from ..utils.references import process_references_from_search_results


logger = logging.getLogger(__name__)


class Curator:
    def __init__(self) -> None:
        self.relevance_threshold = 0.4
        logger.info(f"Curator initialized with relevance threshold: {self.relevance_threshold}")

    async def evaluate_documents(self, state: ResearchState, docs: list, context: Dict[str, str]) -> list:
        """
        Enhanced document evaluation with better WebSocket updates and error handling.
        """
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                logger.info(f"Sending initial curation status update for job {job_id}")
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Evaluating documents",
                    result={"step": "Curation"}
                )
        
        if not docs:
            logger.warning("No documents provided for evaluation")
            return []
        
        logger.info(f"Evaluating {len(docs)} documents")
        evaluated_docs = []
        
        try:
            for doc in docs:
                try:
                    tavily_score = float(doc.get('score', 0))
                    if tavily_score >= self.relevance_threshold:
                        logger.info(f"Document passed threshold with score {tavily_score:.4f} for '{doc.get('title', 'No title')}'")
                        evaluated_doc = {
                            **doc,
                            "evaluation": {
                                "overall_score": tavily_score,
                                "query": doc.get('query', ''),
                                "relevance_reason": f"Score {tavily_score:.4f} meets threshold {self.relevance_threshold}"
                            }
                        }
                        evaluated_docs.append(evaluated_doc)
                        
                        # Send WebSocket update for kept documents
                        if websocket_manager := state.get('websocket_manager'):
                            if job_id := state.get('job_id'):
                                await websocket_manager.send_status_update(
                                    job_id=job_id,
                                    status="document_kept",
                                    message=f"Kept document: {doc.get('title', 'No title')}",
                                    result={
                                        "step": "Curation",
                                        "doc_type": doc.get('doc_type', 'unknown'),
                                        "title": doc.get('title', 'No title'),
                                        "score": tavily_score,
                                        "url": doc.get('url', '')
                                    }
                                )
                    else:
                        logger.info(f"Document below threshold with score {tavily_score:.4f} for '{doc.get('title', 'No title')}'")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing score for document '{doc.get('title', 'Unknown')}': {e}")
                    continue
        except Exception as e:
            logger.error(f"Error during document evaluation: {e}")
            return []
        
        # Sort by score in descending order
        evaluated_docs.sort(key=lambda x: float(x['evaluation']['overall_score']), reverse=True)
        logger.info(f"Returning {len(evaluated_docs)} evaluated documents")
        return evaluated_docs

    def _extract_employee_count_from_company_data(self, company_data: Dict) -> Dict[str, int]:
        """
        Extract employee count from company data as a fallback mechanism.
        """
        valid_employee_counts = {}
        
        for url, data in company_data.items():
            if isinstance(data, dict):
                # Check for employee_count field
                if 'employee_count' in data:
                    emp_count = data['employee_count']
                    if isinstance(emp_count, (int, float)) and emp_count > 0:
                        clean_count = int(emp_count)
                        if 1 <= clean_count <= 10000000:
                            valid_employee_counts[url] = clean_count
                            logger.info(f"CURATION DEBUG - Extracted employee count from company_data: {clean_count} for {url}")
                        else:
                            logger.warning(f"CURATION DEBUG - Employee count {clean_count} outside reasonable range for {url}")
                    else:
                        logger.warning(f"CURATION DEBUG - Invalid employee count in company_data: {emp_count} for {url}")
        
        return valid_employee_counts

    def build_enrichment_counts(self, state: ResearchState) -> Dict[str, Dict[str, int]]:
        """
        Enhanced enrichment counts builder with robust employee count handling.
        """
        company_data = state.get('company_data', {})
        
        # Get employee count from state (set by company analyzer)
        employee_count_dict = state.get('employee_count', {})
        company_count = state.get('Company_Count', 0)
        
        logger.info(f"CURATION DEBUG - Building enrichment counts:")
        logger.info(f"CURATION DEBUG - Employee count dict: {employee_count_dict}")
        logger.info(f"CURATION DEBUG - Company count: {company_count}")
        logger.info(f"CURATION DEBUG - Company data keys: {list(company_data.keys())}")
        # Enhanced validation and processing of employee count data
        valid_employee_counts = {}
        total_employee_count = 0
        
        if employee_count_dict:
            # Filter for valid employee counts with better validation
            for url, count in employee_count_dict.items():
                if isinstance(count, (int, float)) and count > 0:
                    clean_count = int(count)
                    # Validate reasonable range (1 to 10 million employees)
                    if 1 <= clean_count <= 10000000:
                        valid_employee_counts[url] = clean_count
                        total_employee_count += clean_count
                    else:
                        logger.warning(f"Employee count {clean_count} outside reasonable range for {url}")
            
            logger.info(f"CURATION DEBUG - Valid employee counts: {valid_employee_counts}")
            logger.info(f"CURATION DEBUG - Total employee count: {total_employee_count}")
        
        # Fallback: extract from company_data if state data is missing or invalid
        if not valid_employee_counts and company_data:
            logger.warning("No valid employee counts found in state, attempting to extract from company_data")
            valid_employee_counts = self._extract_employee_count_from_company_data(company_data)
            total_employee_count = sum(valid_employee_counts.values())
        
        # Update state with validated values
        if valid_employee_counts:
            state['employee_count'] = valid_employee_counts
            state['Company_Count'] = len(valid_employee_counts)
            logger.info(f"CURATION DEBUG - Updated state with validated employee counts")
        else:
            # Ensure we have at least some structure even if empty
            logger.warning("CURATION DEBUG - No valid employee count data found, using empty structure")
            state['employee_count'] = {}
            state['Company_Count'] = 0

        # Build enrichment counts with enhanced structure
        enrichment_counts = {
            "company": {
                "enriched": len(state.get('curated_company_data', {})),
                "total": len(company_data),
            },
            "employeeCount": {   # camelCase for frontend compatibility
                "enriched": total_employee_count,
                "total": 1,  # We're analyzing one company
                "data": valid_employee_counts,  # Include actual data for frontend
                "hasData": bool(valid_employee_counts and total_employee_count > 0),
                "totalCount": total_employee_count,
                "validCounts": len(valid_employee_counts)
            },
            "industry": {
                "enriched": len(state.get('curated_industry_data', {})),
                "total": len(state.get('industry_data', {})),
            },
            "financial": {
                "enriched": len(state.get('curated_financial_data', {})),
                "total": len(state.get('financial_data', {})),
            },
            "news": {
                "enriched": len(state.get('curated_news_data', {})),
                "total": len(state.get('news_data', {})),
            },
        }
        
        logger.info(f"CURATION DEBUG - Final enrichment counts: {enrichment_counts}")
        logger.info(f"CURATION DEBUG - Employee count section: {enrichment_counts.get('employeeCount', {})}")
        print("\n"*2)
        return enrichment_counts

    async def _send_enrichment_update(self, state: ResearchState, enrichment_counts: Dict):
        """
        Send enrichment counts update via WebSocket with proper error handling.
        """
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')
        
        if websocket_manager and job_id:
            try:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="enrichment_update",
                    message="Enrichment counts updated",
                    result={
                        "step": "Enrichment Update",
                        "enrichmentCounts": enrichment_counts,
                        "timestamp": logger.handlers[0].formatter.formatTime(
                            logger.handlers[0].formatter.converter(None)
                        ) if logger.handlers else None
                    }
                )
                logger.info("Successfully sent enrichment counts update via WebSocket")
            except Exception as e:
                logger.error(f"Error sending enrichment counts update: {e}")

    def _preserve_critical_state_data(self, state: ResearchState) -> Dict[str, any]:
        """
        Preserve critical state data that should not be lost during curation.
        """
        preserved_data = {
            'employee_count': dict(state.get('employee_count', {})),
            'Company_Count': state.get('Company_Count', 0),
            'enrichment_counts': dict(state.get('enrichment_counts', {}))
        }
        
        logger.info(f"CURATION DEBUG - Preserving critical state data: {preserved_data}")
        return preserved_data

    def _restore_critical_state_data(self, state: ResearchState, preserved_data: Dict[str, any]):
        """
        Restore critical state data after curation processing.
        """
        logger.info(f"CURATION DEBUG - Restoring critical state data")
        
        # Restore employee count data
        if preserved_data.get('employee_count'):
            state['employee_count'] = preserved_data['employee_count']
            state['Company_Count'] = preserved_data['Company_Count']
            logger.info(f"CURATION DEBUG - Restored employee_count: {state['employee_count']}")
            logger.info(f"CURATION DEBUG - Restored Company_Count: {state['Company_Count']}")
        
        # Restore enrichment counts if they existed
        if preserved_data.get('enrichment_counts'):
            # Merge with current enrichment counts, preserving employee count data
            current_counts = state.get('enrichment_counts', {})
            if 'employeeCount' in preserved_data['enrichment_counts']:
                current_counts['employeeCount'] = preserved_data['enrichment_counts']['employeeCount']
                state['enrichment_counts'] = current_counts
                logger.info(f"CURATION DEBUG - Restored enrichment counts with employee data")

    async def curate_data(self, state: ResearchState) -> ResearchState:
        """
        Enhanced data curation with better employee count preservation and WebSocket updates.
        """
        company = state.get('company', 'Unknown Company')
        logger.info(f"Starting curation for company: {company}")
        
        # Preserve critical state data before curation
        preserved_data = self._preserve_critical_state_data(state)
        
        # Send initial WebSocket update
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                logger.info(f"Sending initial curation status update for job {job_id}")
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Starting document curation for {company}",
                    result={
                        "step": "Curation",
                        "company": company,
                        "doc_counts": {
                            "company": {"initial": 0, "kept": 0},
                            "industry": {"initial": 0, "kept": 0},
                            "financial": {"initial": 0, "kept": 0},
                            "news": {"initial": 0, "kept": 0}
                        }
                    }
                )
        
        industry = state.get('industry', 'Unknown')
        context = {
            "company": company,
            "industry": industry,
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        msg = [f"🔍 Curating research data for {company}"]
        
        data_types = {
            'financial_data': ('💰 Financial', 'financial'),
            'news_data': ('📰 News', 'news'),
            'industry_data': ('🏭 Industry', 'industry'),
            'company_data': ('🏢 Company', 'company')
        }
        
        # Prepare curation tasks
        curation_tasks = []
        for data_field, (emoji, doc_type) in data_types.items():
            data = state.get(data_field, {})
            if not data:
                logger.info(f"No data found for {data_field}")
                continue
                
            unique_docs = {}
            for url, doc in data.items():
                try:
                    parsed = urlparse(url)
                    if not parsed.scheme:
                        url = urljoin('https://', url)
                    clean_url = parsed._replace(query='', fragment='').geturl()
                    
                    if clean_url not in unique_docs:
                        doc['url'] = clean_url
                        doc['doc_type'] = doc_type
                        unique_docs[clean_url] = doc
                except Exception as e:
                    logger.warning(f"Error processing URL {url}: {e}")
                    continue
            
            docs = list(unique_docs.values())
            curation_tasks.append((data_field, emoji, doc_type, list(unique_docs.keys()), docs))
        
        # Process each data type
        doc_counts = {}
        for data_field, emoji, doc_type, urls, docs in curation_tasks:
            msg.append(f"\n{emoji}: Found {len(docs)} documents")
            
            # Send category start update
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="category_start",
                        message=f"Processing {doc_type} documents",
                        result={
                            "step": "Curation",
                            "doc_type": doc_type,
                            "initial_count": len(docs)
                        }
                    )
            
            # Evaluate documents
            evaluated_docs = await self.evaluate_documents(state, docs, context)
            
            if not evaluated_docs:
                msg.append("  ⚠️ No relevant documents found")
                doc_counts[data_field] = {"initial": len(docs), "kept": 0}
                continue
            
            # Process and sort relevant documents
            relevant_docs = {url: doc for url, doc in zip(urls, evaluated_docs)}
            sorted_items = sorted(
                relevant_docs.items(), 
                key=lambda item: item[1]['evaluation']['overall_score'], 
                reverse=True
            )
            
            # Limit to top 30 documents per category
            if len(sorted_items) > 30:
                sorted_items = sorted_items[:30]
                logger.info(f"Limited {doc_type} documents to top 30 out of {len(relevant_docs)}")
            
            relevant_docs = dict(sorted_items)
            doc_counts[data_field] = {
                "initial": len(docs),
                "kept": len(relevant_docs)
            }
            
            if relevant_docs:
                msg.append(f"  ✅ Kept {len(relevant_docs)} relevant documents")
                logger.info(f"Kept {len(relevant_docs)} documents for {doc_type} with scores above threshold")
            else:
                msg.append("  ⚠️ No documents met relevance threshold")
                logger.info(f"No documents met relevance threshold for {doc_type}")
            
            # Store curated data
            state[f'curated_{data_field}'] = relevant_docs
        
        # Restore critical state data after curation processing
        self._restore_critical_state_data(state, preserved_data)
        
        # Process references using the references module
        try:
            top_reference_urls, reference_titles, reference_info = process_references_from_search_results(state)
            logger.info(f"Selected top {len(top_reference_urls)} references for the report")
            
            state['references'] = top_reference_urls
            state['reference_titles'] = reference_titles
            state['reference_info'] = reference_info
        except Exception as e:
            logger.error(f"Error processing references: {e}")
            state['references'] = []
            state['reference_titles'] = {}
            state['reference_info'] = {}

        # Build enrichment counts (including employee count) - this will validate and update the state
        enrichment_counts = self.build_enrichment_counts(state)
        state['enrichmentCounts'] = enrichment_counts
        
        logger.info(f"CURATION DEBUG - Final enrichment counts being sent to frontend: {enrichment_counts}")
        logger.info(f"CURATION DEBUG - Employee count data in final counts: {enrichment_counts.get('employeeCount', {})}")
        print("\n"*2)
        # Update messages
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages

        # Send final WebSocket update with complete enrichment counts
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="curation_complete",
                    message="Document curation complete",
                    result={
                        "step": "Curation Complete",
                        "enrichmentCounts": enrichment_counts,
                        "doc_counts": {
                            "company": doc_counts.get('company_data', {"initial": 0, "kept": 0}),
                            "industry": doc_counts.get('industry_data', {"initial": 0, "kept": 0}),
                            "financial": doc_counts.get('financial_data', {"initial": 0, "kept": 0}),
                            "news": doc_counts.get('news_data', {"initial": 0, "kept": 0})
                        },
                        # Enhanced employee count data for debugging
                        "employeeCount": {
                            "enriched": enrichment_counts.get('employeeCount', {}).get('enriched', 0),
                            "total": enrichment_counts.get('employeeCount', {}).get('total', 1),
                            "data": state.get('employee_count', {}),
                            "count": state.get('Company_Count', 0),
                            "hasData": enrichment_counts.get('employeeCount', {}).get('hasData', False),
                            "totalCount": enrichment_counts.get('employeeCount', {}).get('totalCount', 0)
                        }
                    }
                )
        
        # Send additional enrichment update
        await self._send_enrichment_update(state, enrichment_counts)
        
        logger.info(f"Curation complete for {company}. Total documents curated: {sum(counts.get('kept', 0) for counts in doc_counts.values())}")
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        """
        Main entry point for the curator with enhanced error handling.
        """
        try:
            return await self.curate_data(state)
        except Exception as e:
            logger.error(f"Critical error in Curator.run: {e}")
            # Ensure we don't lose employee count data even in error cases
            if 'employee_count' not in state:
                state['employee_count'] = {}
            if 'Company_Count' not in state:
                state['Company_Count'] = 0
            
            # Build minimal enrichment counts for error case
            enrichment_counts = self.build_enrichment_counts(state)
            state['enrichmentCounts'] = enrichment_counts
            
            return state