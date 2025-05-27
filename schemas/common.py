from pydantic import BaseModel, Field
from typing import List

class Company(BaseModel):
    name: str = Field(description="Name of the company")
    url: str = Field(description="Url of the company")
    description: str = Field(description="A comprehensive 5-paragraph description of the company that explains its business operations and demonstrates how it relates to the specified capabilities or shows similarity to the provided companies.")
    country: str = Field(description="Country where the company is based")
    industry: str = Field(description="Industry of the company")
    size: str = Field(description="Size of the company")
    founded: str = Field(description="Year the company was founded")

class CompanySearchResult(BaseModel):
    search_strategy: str = Field(description="The search strategy used to find the companies")
    companies: List[Company]
    
class CompanyCapabilities(BaseModel):
    description: str = Field(description="A comprehensive description of the company that explains its business operations, what it does, the different products and services it offers.")
    products_and_services_info: str = Field(description="A list of the products and services the company offers, with a detailed description of each.")
    extraction_reasoning: str = Field(description="The reasoning for the capabilities of the company, ensuring the capabilities best represent the company's business operations and will be useful for the search to find more similar companies.")
    identified_capabilities: List[str] = Field(description="Up to 5 capabilities which best represent the company's business operations and will be useful for the search to find more similar companies.")

class QueryRefinement(BaseModel):
    relevant_companies: List[str] = Field(description="A full list of companies that are relevant to the query.")
    additional_query: str = Field(description="Additional query to improve the search. Goal is to have returned result more relevant to our needs of finding companies that are related to the specified capabilities.")
    

