import asyncio
import logging
import sys
import os
from typing import List, Dict, Any, Literal, Optional, Set
from dataclasses import dataclass
from pydantic import BaseModel, Field
import re
import json

# Add project root to Python path when running this script directly
if __name__ == "__main__":
    # Get the project root directory (parent of services directory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from clients.openai_client import OpenAIClient
from schemas.common import CompanySearchResult, CompanyCapabilities, QueryRefinement

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class RegionalCompanyFinder:
    """Service for finding companies in specific regions using multiple web searches"""

    # Country to major city mapping
    COUNTRY_TO_CITY = {
        "GB": "London",
        "DE": "Berlin", 
        "FR": "Paris",
        "IT": "Rome",
        "FI": "Helsinki",
        "NL": "Amsterdam",
        "BE": "Brussels",
        "DK": "Copenhagen",
        "SE": "Stockholm",
        "NO": "Oslo",
        "EE": "Tallinn",
        "MY": "Kuala Lumpur",
        "ID": "Jakarta",
        "PH": "Manila",
        "TH": "Bangkok",
        "VN": "Hanoi",
        "SG": "Singapore",
        "AE": "Dubai",
        "SA": "Riyadh",
        "KW": "Kuwait City",
        "BH": "Manama",
        "QA": "Doha",
        "JP": "Tokyo",
        "KR": "Seoul",
        "CN": "Beijing"
    }

    def __init__(self, openai_client: Optional[OpenAIClient] = None,
                 seed_company: str = None,
                 capabilities: List[str] = ['narrative intelligence', 'disinformation detection', 'Information Operations (IO) Defense', 'inauthentic online behaviour detection']):
        """
        Initialize the company finder service

        Args:
            openai_client: OpenAI client instance. If None, creates a new one.
            capabilities: List of capabilities to search for in companies
        """
        self.client = openai_client or OpenAIClient()
        self.seed_company = seed_company
        if self.seed_company:
            self._determine_company_capabilities(self.seed_company)
        else:
            self.capabilities = capabilities
        self.seed_company_description = None
        self.relevant_companies = []
        self.additional_query = ""
        
    def _determine_company_capabilities(self, company_name: str) -> CompanyCapabilities:
        """
        Analyze a company and determine its capabilities using OpenAI
        
        Args:
            company_name: Name of the company to analyze
            
        Returns:
            CompanyCapabilities object with identified capabilities and confidence scores
        """
        try:
            # Build analysis query with assumptions about company domain
            query = f"""
            Analyze the company "{company_name}" and determine which capabilities it possesses.
            
            Assumptions about the company:
            - The company operates in military, social media analytics, and/or tech-related domains
            - It likely provides services or products related to defense, social media analysis, or technology solutions
            
            Research this company online and determine:
            1. What specific services or products does this company offer?
            2. Which capabilities from the target list does the company possess based on their business focus, services, or expertise?
            
            Only include capabilities that you are reasonably confident the company actually possesses based on available information.
            """
            
            logger.info(f"Analyzing capabilities for company: {company_name}")
            
            # Use web search to get information about the company
            response = self.client.web_search(
                query=query,
                search_context_size="high",
                text_format=CompanyCapabilities
            )
            
            # Extract the structured result
            content = json.loads(response.output[1].content[0].text)
            result = CompanyCapabilities.model_validate(content)
            
            # Store the result in the instance variable
            self.capabilities = result.identified_capabilities
            print(f"Capabilities: {self.capabilities}")
            self.seed_company_description = result.description
            
            logger.info(f"Identified {len(result.identified_capabilities)} capabilities for {company_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error determining capabilities for {company_name}: {e}")
            # Return empty result on error
            error_result = CompanyCapabilities(
                identified_capabilities=[],
            )
            # Store the error result as well
            self.capabilities = error_result.identified_capabilities
            return error_result

    def _generate_search_queries(self, country: str) -> List[str]:
        """
        Generate diverse search queries to find companies in a region

        Args:
            country: The country to search in

        Returns:
            List of search query strings
        """
        base_queries = [f"Companies in {country} that are related to {capability}" for capability in self.capabilities]
        
        # Return the requested number of queries, cycling through if needed
        return base_queries

    async def _search_companies_single_query(self, query: str, user_location: Optional[Dict[str, Any]] = None, found_companies: Optional[List[str]] = None) -> CompanySearchResult:
        """
        Perform a single web search for companies

        Args:
            query: Search query string
            user_location: Optional location information for localized results
            found_companies: List of already found company names to avoid repeating

        Returns:
            CompanySearchResult with structured data
        """
        try:
            logger.info(f"Searching with query: {query}")

            response = await self.client.web_search_async(
                query=query,
                user_location=user_location,
                search_context_size="high",
                text_format=CompanySearchResult
            )

            # Extract the structured result
            content = json.loads(response.output[1].content[0].text)
            # Try to parse as CompanySearchResult if it's structured
            try:
                return CompanySearchResult.model_validate(content)
            except Exception as parse_error:
                logger.warning(f"Failed to parse result as CompanySearchResult: {parse_error}")
                # Return the raw content as fallback
                return content

        except Exception as e:
            logger.error(f"Error in single query search: {e}")
            return CompanySearchResult(
                search_strategy="error",
                companies=[]
            )
            
    def _get_user_location(self, country: str) -> Dict[str, Any]:
        return {
            "type": "approximate",
            "country": country,
            "region": self.COUNTRY_TO_CITY.get(country, "Unknown"),
            "city": self.COUNTRY_TO_CITY.get(country, "Unknown")
        }
    def _get_user_locations(self, region: Literal["EU", "ASEAN", "MENA", "ASIA(CN/JP/KR)"]) -> List[Dict[str, Any]]:
        """
        Get user locations based on region

        Args:
            region: The region/city to search in

        Returns:
            List of user locations
        """
        # Define countries for each region
        region_countries = {
            "EU": ["GB", "DE", "FR", "IT", "FI", "NL", "BE", "DK", "SE", "NO", "EE"],
            "ASEAN": ["MY", "ID", "PH", "TH", "VN", "SG"],
            "MENA": ["AE", "SA", "KW", "BH", "QA"],
            "ASIA(CN/JP/KR)": ["JP", "KR", "CN"]
        }
        
        # Get countries for the specified region
        countries = region_countries.get(region, [])
        
        # Use _get_user_location for each country
        return [self._get_user_location(country) for country in countries]
    
    def _deduplicate_companies(self, all_companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate companies based on name similarity

        Args:
            all_companies: List of company dictionaries

        Returns:
            Deduplicated list of companies
        """
        seen_names = set()
        unique_companies = []

        for company in all_companies:
            name = company.get('name', '').lower().strip()
            # Simple deduplication - could be enhanced with fuzzy matching
            if name and name not in seen_names:
                seen_names.add(name)
                unique_companies.append(company)

        return unique_companies

    async def find_companies_in_country(
        self,
        country: str,
        user_location: Optional[Dict[str, Any]] = None,
        refined_additional_query: Optional[str] = None,
        refined_relevant_companies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Find companies in a specified country by running multiple web searches

        Args:
            country: The country to search in (e.g., "USA", "UK", "GB")
            user_location: Optional location info for localized search results
            refined_additional_query: Optional additional query to use for search
            refined_relevant_companies: Optional list of relevant companies to use for search

        Returns:
            Dictionary containing:
                - companies: List of unique companies found
                - total_found: Total number of unique companies
                - search_queries_used: List of queries that were executed
                - summary: Summary of the search process
        """
        logger.info(f"Starting company search for {country}")
        
        # Set up user location if not provided
        if user_location is None:
            user_location = self._get_user_location(country)
            
        # Generate search queries
        search_queries = self._generate_search_queries(country)
        
        # Perform all searches sequentially
        all_companies = []
        successful_searches = 0
        found_company_names = []  # Track company names to avoid repetition
        executed_queries = []  # Track the actual enhanced queries that were executed

        for i, query in enumerate(search_queries):
            logger.info(f"Executing search {i+1}/{len(search_queries)}")

            # Determine which relevant_companies and additional_query to use for this specific search iteration
            _additional_query_to_use = refined_additional_query if refined_additional_query is not None else self.additional_query
            _relevant_companies_to_use = refined_relevant_companies if refined_relevant_companies is not None else self.relevant_companies

            # Create the enhanced query
            if found_company_names:
                # Limit to first 20 to avoid too long queries
                companies_context = ", ".join(found_company_names[:20])
                
                if self.seed_company:
                    enhanced_query = f"{query}. Find companies similar to {self.seed_company} but NOT including these already found: {companies_context}. Do not repeat any of these companies."
                else:
                    enhanced_query = f"{query}. NOT including these already found: {companies_context}. Do not repeat any of these companies."
            elif _relevant_companies_to_use:
                relevant_companies_str = ", ".join(_relevant_companies_to_use)
                enhanced_query = f"{query}. Find companies similar to these: {relevant_companies_str}. Do not repeat any of these companies."
            elif self.seed_company: # Fallback to seed_company if no found_company_names and no _relevant_companies_to_use
                enhanced_query = f"{query}. Find companies similar to {self.seed_company}."
            else:
                enhanced_query = query
            
            if _additional_query_to_use:
                enhanced_query = f"{enhanced_query} {_additional_query_to_use}"
            
            # Track the actual query that will be executed
            executed_queries.append(enhanced_query)

            result = await self._search_companies_single_query(
                enhanced_query, # Pass the fully constructed enhanced_query
                user_location,
                # Pass found companies starting from second search (this is for _search_companies_single_query's internal context if it uses it, not for query construction here)
                found_company_names if i > 0 else None
            )

            if isinstance(result, Exception):
                logger.error(f"Search {i+1} failed: {result}")
                continue
            
            logger.info(f"Search result type: {type(result)}, value: {result}")
            
            # Handle both CompanySearchResult instances and dictionaries
            if isinstance(result, CompanySearchResult):
                new_companies = [company.model_dump() if hasattr(company, 'model_dump') else company for company in result.companies]
            elif isinstance(result, dict) and 'companies' in result:
                # Convert dictionary result to proper format
                new_companies = result['companies']
            else:
                logger.warning(f"Search {i+1} returned unexpected result format: {type(result)}")
                continue

            all_companies.extend(new_companies)

            # Extract company names for future searches
            for company in new_companies:
                if company.get('name'):
                    found_company_names.append(company['name'])

            successful_searches += 1
            logger.info(
                f"Search {i+1} found {len(new_companies)} companies. Total so far: {len(all_companies)}")

            # Add a small delay between searches to be respectful to the API
            if i < len(search_queries) - 1:  # Don't delay after the last search
                await asyncio.sleep(1)

        # Deduplicate companies
        unique_companies = self._deduplicate_companies(all_companies)

        logger.info(
            f"Found {len(unique_companies)} unique companies from {successful_searches} successful searches in {country}")

        return {
            "companies": unique_companies,
            "total_found": len(unique_companies),
            "search_queries_used": executed_queries,  # Now contains the actual enhanced queries that were executed
            "successful_searches": successful_searches,
            "total_searches": len(search_queries),
            "summary": f"Found {len(unique_companies)} unique companies in {country} from {successful_searches}/{len(search_queries)} successful searches"
        }

    async def _deep_search_single_country(self, country: str, user_location: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform a deep search for companies in a single country.
        This involves an initial search, query refinement based on results, and a second search.
        """
        if user_location is None:
            user_location = self._get_user_location(country)

        logger.info(f"Running DEEP SEARCH for {country}")
        
        logger.info("Phase 1: Initial search...")
        # Initial search does not use any specific refined parameters beyond what might already be in self.additional_query or self.relevant_companies (e.g. from a previous unrelated call or initial state)
        result = await self.find_companies_in_country(country, user_location)
        logger.info(f"Phase 1 complete: Found {result['total_found']} companies")
        
        logger.info("Phase 2: Refining query based on initial results...")
        query_refinement_output = await self.refine_query(str(result))
        # Use the returned values from refine_query directly as local variables
        local_additional_query = query_refinement_output.additional_query
        local_relevant_companies = query_refinement_output.relevant_companies
        phase1_relevant_company_names = local_relevant_companies # Names of relevant companies from phase 1 refinement

        logger.info(f"Refined additional query for {country}: {local_additional_query}")
        logger.info(f"Refined relevant companies for {country}: {local_relevant_companies}")

        logger.info("Phase 3: Running refined search...")
        # Pass the locally obtained additional_query and relevant_companies to the second search
        refined_result = await self.find_companies_in_country(
            country,
            user_location,
            refined_additional_query=local_additional_query,
            refined_relevant_companies=local_relevant_companies
        ) 
        logger.info(f"Phase 3 complete: Found {refined_result['total_found']} companies initially in refined search")

        # Combine results:
        # Take relevant companies found in Phase 1 (full dicts)
        # Add all companies from Phase 2 (refined_result)
        # Deduplicate
        
        phase1_all_company_dicts = result.get('companies', [])

        # Filter Phase 1 company dictionaries to keep only those whose names are in phase1_relevant_company_names
        filtered_phase1_relevant_company_dicts = [
            company_dict for company_dict in phase1_all_company_dicts
            if company_dict.get('name') in phase1_relevant_company_names
        ]
        
        # Combine the filtered list of relevant company dicts from Phase 1
        # with all company dicts from Phase 2 (refined_result['companies'])
        combined_companies = filtered_phase1_relevant_company_dicts + refined_result.get('companies', [])
        
        unique_combined_companies = self._deduplicate_companies(combined_companies)
        
        # Update the refined_result structure to be the final output
        refined_result['companies'] = unique_combined_companies
        refined_result['total_found'] = len(unique_combined_companies)
        # The summary and query details in refined_result will primarily reflect the second pass.
        # This matches the behavior of the original convenience function's deep search.
        refined_result['summary'] = f"Deep search found {len(unique_combined_companies)} unique companies in {country} after refinement. (Phase 1: {result['total_found']}, Phase 2: {refined_result['total_found']} before merge)"


        logger.info(f"Deep search for {country}: Total unique companies after combining and deduplicating: {refined_result['total_found']}")
        logger.info(f"DEEP SEARCH for {country} completed!")
        return refined_result

    async def find_companies_in_region(
        self,
        region: Literal["EU", "ASEAN", "MENA", "ASIA(CN/JP/KR)"],
        deep_search: bool = False
    ) -> Dict[str, Any]:
        """
        Find companies in a specified region by running find_companies_in_country 
        asynchronously for each country in the region

        Args:
            region: The region to search in (e.g., "EU", "ASEAN", "MENA", "ASIA(CN/JP/KR)")

        Returns:
            Dictionary containing:
                - companies: List of unique companies found across all countries
                - total_found: Total number of unique companies
                - countries_searched: List of countries that were searched
                - country_results: Dictionary with results per country
                - summary: Summary of the search process
        """
        logger.info(f"Starting comprehensive company search for region: {region}")

        # Get user locations for the region
        user_locations = self._get_user_locations(region)
        
        # Extract unique country codes
        countries = [location["country"] for location in user_locations]
        unique_countries = list(set(countries))  # Remove duplicates
        
        logger.info(f"Searching in {len(unique_countries)} countries: {unique_countries}")

        # Create tasks for each country search
        tasks = []
        for country in unique_countries:
            # Find the corresponding user_location for this country
            user_location = next((loc for loc in user_locations if loc["country"] == country), None)
            
            if deep_search:
                task = self._deep_search_single_country(country, user_location)
            else:
                task = self.find_companies_in_country(country, user_location)
            tasks.append((country, task))

        # Run all country searches concurrently
        logger.info("Running country searches concurrently...")
        
        all_companies = []
        country_results = {}
        successful_countries = 0
        total_searches = 0
        total_successful_searches = 0

        # Execute all tasks concurrently
        country_tasks = [task for _, task in tasks]
        self.results = results = await asyncio.gather(*country_tasks, return_exceptions=True)
        
        # Process results
        for i, ((country, _), result) in enumerate(zip(tasks, results)):
            if isinstance(result, Exception):
                logger.error(f"Search for {country} failed: {result}")
                country_results[country] = {
                    "error": str(result),
                    "companies": [],
                    "total_found": 0
                }
                continue
            
            # Store country-specific results
            country_results[country] = result
            all_companies.extend(result["companies"])
            successful_countries += 1
            total_searches += result.get("total_searches", 0)
            total_successful_searches += result.get("successful_searches", 0)
            
            logger.info(f"Country {country}: Found {result['total_found']} companies")

        # Deduplicate companies across all countries
        unique_companies = self._deduplicate_companies(all_companies)

        logger.info(
            f"Found {len(unique_companies)} unique companies across {successful_countries}/{len(unique_countries)} countries in {region}")

        return {
            "companies": unique_companies,
            "total_found": len(unique_companies),
            "countries_searched": unique_countries,
            "successful_countries": successful_countries,
            "total_countries": len(unique_countries),
            "country_results": country_results,
            "total_searches": total_searches,
            "total_successful_searches": total_successful_searches,
            "summary": f"Found {len(unique_companies)} unique companies across {successful_countries}/{len(unique_countries)} countries in {region} region. Total searches: {total_successful_searches}/{total_searches}"
        }

    async def refine_query(self, prev_search_result_str: str) -> QueryRefinement:
        """
        Refine a query to improve the search results based on previously found companies and the queries applied.

        Args:
            prev_search_result_str: String representation of the previous search result dictionary.
            
        Returns:
            QueryRefinement object with refined query and reason
        """
        try:
            response = await self.client.reasoning_async(
                query=prev_search_result_str,
                text_format=QueryRefinement
            )
            json_text = response.output[1].content[0].text
            data_dict = json.loads(json_text)
            query_refinement_obj = QueryRefinement.model_validate(data_dict)
            
            # DO NOT store in instance variables anymore
            # self.additional_query = query_refinement_obj.additional_query
            # self.relevant_companies = query_refinement_obj.relevant_companies
            
            # Log what was refined, but it's now up to the caller to use these.
            logger.info(f"Refinement produced additional query: {query_refinement_obj.additional_query}")
            logger.info(f"Refinement produced relevant companies: {query_refinement_obj.relevant_companies}")
            return query_refinement_obj
        except Exception as e:
            logger.error(f"Error refining query: {e}")
            return QueryRefinement(
                relevant_companies=[],
                additional_query="")
# Convenience function for easy usage


async def find_companies(
    region: Literal["EU", "ASEAN", "MENA", "ASIA(CN/JP/KR)"],
    openai_client: Optional[OpenAIClient] = None,
    capabilities: Optional[List[str]] = None,
    seed_company: Optional[str] = None,
    deep_search: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to find companies in a region

    Args:
        region: The region to search in (e.g., "EU", "ASEAN", "MENA", "ASIA(CN/JP/KR)")
        openai_client: Optional OpenAI client instance
        capabilities: Optional list of capabilities to search for. Uses default if None.
        seed_company: Optional seed company name to use for search
    Returns:
        Dictionary with company search results
    """
    if capabilities is None:
        finder = RegionalCompanyFinder(openai_client, seed_company)
    else:
        finder = RegionalCompanyFinder(openai_client, seed_company, capabilities)
    return await finder.find_companies_in_region(region, deep_search)


async def find_companies_in_country(
    country: str,
    openai_client: Optional[OpenAIClient] = None,
    capabilities: Optional[List[str]] = None,
    seed_company: Optional[str] = None,
    deep_search: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to find companies in a specific country

    Args:
        country: The country to search in (e.g., "USA", "UK", "GB")
        openai_client: Optional OpenAI client instance
        capabilities: Optional list of capabilities to search for. Uses default if None.
        seed_company: Optional seed company name to use for search
        deep_search: Whether to perform a multi-pass deep search.
    Returns:
        Dictionary with company search results
    """
    finder_kwargs = {"openai_client": openai_client, "seed_company": seed_company}
    if capabilities is not None:
        finder_kwargs["capabilities"] = capabilities
    finder = RegionalCompanyFinder(**finder_kwargs)
    
    # User location will be handled by the class methods if not passed or passed as None.
    if not deep_search:
        logger.info(f"Running standard search for {country} via convenience function.")
        return await finder.find_companies_in_country(country)
    else:
        logger.info(f"Running DEEP SEARCH for {country} via convenience function.")
        return await finder._deep_search_single_country(country)

# Example usage
if __name__ == "__main__":
    # Get the project root directory (parent of services directory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def example_usage():
        import datetime
        
        # Create a timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Example: Find companies in EU region (searches across all EU countries)
        print("Region-based search example:")
        results = await find_companies("ASIA(CN/JP/KR)", seed_company = "BlackBird.AI", deep_search=True)

        # Save EU results to JSON
        asia_filename = f"asia_companies_{timestamp}.json"
        with open(asia_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Found {results['total_found']} companies across {results['successful_countries']} countries:")
        print(f"Countries searched: {results['countries_searched']}")
        print(f"Results saved to: {asia_filename}")
        
        # Show first 10 companies for preview
        for company in results['companies'][:10]:
            print(f"- {company['name']}")

        print(f"\nSummary: {results['summary']}")

        # # Example: Find companies in a specific country
        # print("\n" + "="*50)
        # print("Country-specific search example:")
        
        # country_results = await find_companies_in_country("GB",
        #                                                   seed_company = "BlackBird.AI",
        #                                                   deep_search=True)
        
        # # Save GB results to JSON
        # gb_filename = f"gb_companies_{timestamp}.json"
        # with open(gb_filename, 'w', encoding='utf-8') as f:
        #     json.dump(country_results, f, indent=2, ensure_ascii=False)
        
        # print(f"Found {country_results['total_found']} companies in GB:")
        # print(f"Results saved to: {gb_filename}")
        
        # # Show first 10 companies for preview
        # for company in country_results['companies'][:10]:
        #     print(f"- {company['name']}")

        # print(f"\nSummary: {country_results['summary']}")


    # Uncomment to run example
    asyncio.run(example_usage())
