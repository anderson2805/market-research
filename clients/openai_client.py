import os
import asyncio
from typing import  Dict, Any, Literal, Optional
from dotenv import load_dotenv
from openai import OpenAI
from openai import AsyncOpenAI
from openai import RateLimitError
from tenacity import retry, stop_after_delay, wait_exponential, retry_if_exception_type
from pydantic import BaseModel

# Import instructor
import instructor

class OpenAIClient:
    """
    Client for interacting with the OpenAI API with web search capabilities.
    
    Documentation: https://platform.openai.com/docs/api-reference/chat/create
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the OpenAI API client.
        
        Args:
            api_key: OpenAI API key. If None, it will be loaded from environment variables.
            model: Default model to use. If None, it will use gpt-4.1 as default.
        """
        load_dotenv()  # Load environment variables from .env file
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set it in .env file or pass it as argument.")
        
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1")
        
        # Initialize the official OpenAI client
        openai_client = OpenAI(api_key=self.api_key)
        
        # Initialize the async OpenAI client
        async_openai_client = AsyncOpenAI(api_key=self.api_key)

        # Patch the clients with instructor
        self.client = instructor.patch(openai_client)
        self.async_client = instructor.patch(async_openai_client)
    
    def web_search(self, query: str, user_location: Optional[Dict[str, Any]] = None, search_context_size: Literal["low", "medium", "high"] = "high", text_format: Optional[BaseModel] = None) -> Dict[str, Any]:
        """
        Perform a web search using OpenAI's web search preview tool.
        
        Args:
            query: The search query string
            user_location: Optional location information for localized search results.
                          Should be a dict with keys like 'type', 'country', 'city', 'region'
            search_context_size: Optional search context size (e.g., "low", "medium", "high")
            text_format: Optional Pydantic model to structure the response
        
        Returns:
            Dict containing:
                - 'content': The text content with inline citations
                - 'citations': List of citation objects with URL, title, and other metadata
                - 'raw_response': The original response from OpenAI
        """
        # Build the tool configuration
        tool_config = {"type": "web_search_preview"}
        
        # Add optional parameters if provided
        if user_location is not None:
            tool_config["user_location"] = user_location
            
        if search_context_size is not None:
            tool_config["search_context_size"] = search_context_size

        # Build parameters for the responses.parse call
        parse_params = {
            "model": self.model,
            "tools": [tool_config],
            "instructions": "You are a market research analyst assistant. You are given a query and you need to research online and provide a structured response with steps and final answer.",
            "input": query,
            "max_output_tokens": 64000
        }
        
        # Add text_format if provided
        if text_format is not None:
            parse_params["text_format"] = text_format

        response = self.client.responses.parse(**parse_params)

        # Process the response to extract content and citations
        # processed_result = self._process_web_search_response(response)
        
        return response
    
    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_delay(60)
    )
    async def web_search_async(self, query: str, user_location: Optional[Dict[str, Any]] = None, search_context_size: Literal["low", "medium", "high"] = "high", text_format: Optional[BaseModel] = None) -> Dict[str, Any]:
        """
        Async version of web_search. Perform a web search using OpenAI's web search preview tool.
        
        Args:
            query: The search query string
            user_location: Optional location information for localized search results.
                          Should be a dict with keys like 'type', 'country', 'city', 'region'
            search_context_size: Optional search context size (e.g., "low", "medium", "high")
            text_format: Optional Pydantic model to structure the response
        
        Returns:
            Dict containing:
                - 'content': The text content with inline citations
                - 'citations': List of citation objects with URL, title, and other metadata
                - 'raw_response': The original response from OpenAI
        """
        # Build the tool configuration
        tool_config = {"type": "web_search_preview"}
        instructions = "You are a market research analyst assistant. You are given a query and you need to research online and provide a structured response with steps and final answer."
        # Add optional parameters if provided
        if user_location is not None:
            tool_config["user_location"] = user_location
            instructions = f"{instructions} The companies should be based in {user_location['country']}."
            
        if search_context_size is not None:
            tool_config["search_context_size"] = search_context_size

        # Build parameters for the responses.parse call
        parse_params = {
            "model": self.model,
            "tools": [tool_config],
            "instructions": instructions,
            "input": query,
            "max_output_tokens": 64000
        }
        
        # Add text_format if provided
        if text_format is not None:
            parse_params["text_format"] = text_format

        response = await self.async_client.responses.parse(**parse_params)

        # Process the response to extract content and citations
        # processed_result = self._process_web_search_response(response)
        
        return response
    
    def reasoning(self, query: str, text_format: str) -> Dict[str, Any]:
        """
        Perform a reasoning task using OpenAI's reasoning tool.
        
        Args:
            query: The query string
            text: The text to reason about
        
        Returns:
            Dict containing:
                - 'content': The text content with inline citations
                - 'citations': List of citation objects with URL, title, and other metadata
                - 'raw_response': The original response from OpenAI
        """
        model = "o3"
        instructions = "You are a prompt engineer assistant. You are given a query and the result from such query. You need to reason about the query and the result, see what are the pattern of relevant and irrelevant companies. Suggest new sentences to add on the existing query so that the result is more relevant."
        response = self.client.responses.parse(
            model=model,
            instructions=instructions,
            reasoning={"effort": "high"},
            input=query,
            text_format = text_format,
            max_output_tokens=100000
        )
        
        return response
    
    async def reasoning_async(self, query: str, text_format: BaseModel) -> Dict[str, Any]:
        """
        Async version of reasoning. Perform a reasoning task using OpenAI's reasoning tool.
        
        Args:
            query: The query string (can be a string representation of previous results/context)
            text_format: The Pydantic model to structure the response
        
        Returns:
            Dict containing the structured response from OpenAI
        """
        model = "o3"  # Or your preferred model for reasoning
        instructions = "You are a prompt engineer assistant. You are given a query and the result from such query. You need to reason about the query and the result, see what are the pattern of relevant and irrelevant companies. Suggest new sentences to add on the existing query so that the result is more relevant."
        
        response = await self.async_client.responses.parse(
            model=model,
            instructions=instructions,
            reasoning={"effort": "high"},
            input=query,
            text_format=text_format,
            max_output_tokens=100000  # Adjust as needed
        )
        
        return response
    
if __name__ == "__main__":
    import json
    import sys

    client = OpenAIClient()
        # Get the project root directory (parent of services directory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from schemas.common import QueryRefinement

    # # Example of using the async version
    # async def async_example():
    #     response = await client.web_search_async("What is the latest news on the stock market?")
    #     print("Async response:", response)
    
    # # Uncomment to run async example
    # asyncio.run(async_example())
    
    async def reasoning_example():
        with open("asia_companies_20250526_033556.json", "r") as f:
            data = json.load(f)
        response = client.reasoning(str(data), QueryRefinement)
        print(response.output[1])

    asyncio.run(reasoning_example())
