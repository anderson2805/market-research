import streamlit as st
import asyncio
import json
import pandas as pd
from datetime import datetime
from streamlit_tags import st_tags
from io import BytesIO

from services.related_companies import RegionalCompanyFinder, find_companies_in_country, find_companies
from clients.openai_client import OpenAIClient

# Helper function to initialize OpenAIClient and RegionalCompanyFinder
def get_openai_client():
    if "openai_client" not in st.session_state:
        # Load API key and model from Streamlit secrets
        api_key = st.secrets.get("OPENAI_API_KEY")
        model = st.secrets.get("OPENAI_MODEL", "gpt-4.1") # Default to gpt-4.1 if not set
        if not api_key:
            st.error("OpenAI API key not found in Streamlit secrets. Please add it to your secrets.toml file.")
            st.stop()
        st.session_state.openai_client = OpenAIClient(api_key=api_key, model=model)
    return st.session_state.openai_client

def get_company_finder(seed_company=None, capabilities=None):
    client = get_openai_client()
    if capabilities:
        return RegionalCompanyFinder(openai_client=client, seed_company=seed_company, capabilities=capabilities)
    return RegionalCompanyFinder(openai_client=client, seed_company=seed_company)

def show():
    st.title("Market Research Search")

    # Initialize session state variables
    if "company_capabilities" not in st.session_state:
        st.session_state.company_capabilities = []
    if "company_description" not in st.session_state:
        st.session_state.company_description = ""
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "seed_company_input" not in st.session_state:
        st.session_state.seed_company_input = ""
    if "capabilities_tags_input" not in st.session_state:
        default_capabilities_text = "narrative intelligence, disinformation detection, Information Operations (IO) Defense, inauthentic online behaviour detection"
        st.session_state.capabilities_tags_input = [c.strip() for c in default_capabilities_text.split(',') if c.strip()]
    if "tags_version" not in st.session_state:
        st.session_state.tags_version = 0

    # --- Country Code to Name Mapping ---
    COUNTRY_CODE_TO_NAME = {
        "GB": "United Kingdom",
        "DE": "Germany",
        "FR": "France",
        "IT": "Italy",
        "FI": "Finland",
        "NL": "Netherlands",
        "BE": "Belgium",
        "DK": "Denmark",
        "SE": "Sweden",
        "NO": "Norway",
        "EE": "Estonia",
        "MY": "Malaysia",
        "ID": "Indonesia",
        "PH": "Philippines",
        "TH": "Thailand",
        "VN": "Viet Nam",
        "SG": "Singapore",
        "AE": "United Arab Emirates",
        "SA": "Saudi Arabia",
        "KW": "Kuwait",
        "BH": "Bahrain",
        "QA": "Qatar",
        "JP": "Japan",
        "KR": "South Korea", # Officially "Korea (the Republic of)"
        "CN": "China",
        # Add any other countries from your services/related_companies.py if needed
        # For example, if you have US companies: "US": "United States"
    }
    COUNTRY_NAME_TO_CODE = {name: code for code, name in COUNTRY_CODE_TO_NAME.items()}


    # --- Inputs ---
    st.header("Company & Capability Input")

    # Moved label outside and above columns for better alignment control
    st.caption("Enter a company name to find related companies (optional):")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        seed_company = st.text_input(
            label="Seed company input", # Label is still good for backend/keys
            label_visibility="collapsed", # This will hide the label visually and collapse its space
            placeholder="Type company name here...",
            key="seed_company_input"
            )

    with col2:
        # No need for the markdown spacer anymore
        if st.button("Fetch Capabilities", disabled=not st.session_state.seed_company_input, type='primary'):
            if st.session_state.seed_company_input:
                with st.spinner(f"Fetching capabilities for {st.session_state.seed_company_input}..."):
                    try:
                        finder = get_company_finder(seed_company=st.session_state.seed_company_input)
                        # _determine_company_capabilities is not async, but it calls a client method that might be
                        # For simplicity in Streamlit, running sync if underlying calls handle their own loops
                        # or if we decide the primary path here is sync.
                        # If _determine_company_capabilities itself becomes async, need to use asyncio.run()
                        company_cap_obj = finder._determine_company_capabilities(st.session_state.seed_company_input)
                        st.session_state.company_capabilities = company_cap_obj.identified_capabilities
                        st.session_state.company_description = company_cap_obj.description
                        st.session_state.capabilities_tags_input = company_cap_obj.identified_capabilities if company_cap_obj.identified_capabilities else []
                        st.session_state.tags_version += 1
                        st.success(f"Capabilities fetched for {st.session_state.seed_company_input}!")
                    except Exception as e:
                        st.error(f"Error fetching capabilities: {e}")
                        st.session_state.company_capabilities = []
                        st.session_state.company_description = ""
                        st.session_state.capabilities_tags_input = []
                        st.session_state.tags_version += 1

    if st.session_state.company_description:
        with st.expander("Company Description"):
            st.markdown(st.session_state.company_description)

    # Use st_tags for capabilities input
    final_capabilities = st_tags(
        label="Focus on companies with specific capabilities (press Enter after each capability):",
        text='Type and press enter to add',
        value=st.session_state.capabilities_tags_input,
        key=f'capabilities_tags_input_{st.session_state.tags_version}',
        maxtags=-1
    )


    # --- Search Scope & Filters ---
    st.header("Search Scope & Filters")
    search_type = st.radio("Search by:", ("Region", "Country"), horizontal=True, key="search_type_selection")

    target_region = None
    target_country = None

    if search_type == "Region":
        target_region = st.selectbox(
            "Select Region:",
            ("EU", "ASEAN", "MENA", "ASIA(CN/JP/KR)"),
            key="region_selection"
        )
    else: # Country
        country_names = sorted(list(COUNTRY_NAME_TO_CODE.keys()))
        # Add a "Type or select country" option or similar if you want to allow text input as well
        # For now, strictly a dropdown.
        selected_country_name = st.selectbox(
            "Select Country:",
            options=country_names,
            key="country_name_selection",
            index=country_names.index("United Kingdom") if "United Kingdom" in country_names else 0 # Default to UK or first if not available
        )
        if selected_country_name:
            target_country = COUNTRY_NAME_TO_CODE[selected_country_name]
        # Fallback for the key used in download logic, might need adjustment based on usage
        st.session_state.country_input = target_country 

    deep_search = st.checkbox("Enable Deep Search (more comprehensive, slower)", value=True, key="deep_search_toggle")

    # --- Search Execution ---
    if st.button("Search Companies", type="primary"):
        st.session_state.search_results = None # Reset previous results
        client = get_openai_client() # Ensure client is initialized

        if not final_capabilities and not st.session_state.seed_company_input:
            st.warning("Please enter a seed company or define capabilities.")
        elif search_type == "Country" and not target_country:
            st.warning("Please enter a country code for country search.")
        else:
            search_params = {
                "openai_client": client,
                "capabilities": final_capabilities if final_capabilities else None, # Pass None if empty to use defaults
                "seed_company": st.session_state.seed_company_input if st.session_state.seed_company_input else None,
                "deep_search": deep_search
            }

            with st.spinner("Searching for companies... This may take a while, especially with deep search."):
                try:
                    if search_type == "Region":
                        st.info(f"Starting REGION search for: {target_region} with capabilities: {final_capabilities or 'Default'} and seed company: {st.session_state.seed_company_input or 'None'}")
                        results = asyncio.run(find_companies(region=target_region, **search_params))
                    else: # Country
                        st.info(f"Starting COUNTRY search for: {target_country} with capabilities: {final_capabilities or 'Default'} and seed company: {st.session_state.seed_company_input or 'None'}")
                        results = asyncio.run(find_companies_in_country(country=target_country, **search_params))
                    
                    st.session_state.search_results = results
                    st.success("Search complete!")

                except Exception as e:
                    st.error(f"An error occurred during search: {e}")
                    st.session_state.search_results = {"error": str(e), "companies": []}


    # --- Results Display ---
    if st.session_state.search_results:
        st.divider()
        st.header("Search Results")
        results = st.session_state.search_results

        if "error" in results:
            st.error(f"Search failed: {results['error']}")
        elif results and results.get("companies"):
            st.success(results.get("summary", f"Found {results.get('total_found', 0)} companies."))

            companies_df = pd.DataFrame(results["companies"])
            st.metric("Total Companies Found", results.get("total_found", len(results["companies"])))

            if "country_results" in results: # Region search
                st.subheader("Results per Country")
                for country, res in results["country_results"].items():
                    expander_title = f"{country}: {res.get('total_found',0)} companies"
                    if res.get('error'):
                        expander_title += " (Error)"
                    with st.expander(expander_title):
                        if res.get('error'):
                            st.error(f"Error for {country}: {res.get('error')}")
                        elif res.get("companies"):
                            st.dataframe(pd.DataFrame(res["companies"]), use_container_width=True)
                        else:
                            st.info(f"No companies found or data available for {country}.")
            
            st.subheader("Top 20 Companies Preview (All Regions/Countries)")
            st.dataframe(companies_df.head(20), use_container_width=True)

            # Download button
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            search_prefix = target_region.lower() if target_region else target_country.lower()
            
            # JSON Download
            json_filename = f"{search_prefix}_companies_{timestamp}.json"
            json_string = json.dumps(results, indent=2, ensure_ascii=False)
            st.download_button(
                label="Download Full Results (JSON)",
                data=json_string,
                file_name=json_filename,
                mime="application/json",
            )

            # Excel Download
            excel_filename = f"{search_prefix}_companies_{timestamp}.xlsx"
            # Create an in-memory buffer for the Excel file
            excel_buffer = BytesIO()
            # Convert the full DataFrame to Excel, not just the head(20)
            # If results["companies"] is the full list of companies, use it.
            # Assuming 'companies_df' holds all companies based on its previous usage.
            if not companies_df.empty:
                companies_df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0) # Reset buffer position to the beginning
                st.download_button(
                    label="Download Full Results (Excel)",
                    data=excel_buffer,
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("No data to export to Excel.")

        elif results: # Non-empty but no 'companies' key, or 'companies' is empty
             st.info(results.get("summary", "No companies found matching your criteria."))
             if "summary" in results and isinstance(results["summary"], str) and "error" in results["summary"].lower(): # crude error check
                 st.warning(f"Search might have encountered issues: {results['summary']}")
        else: # results is None or empty dict
            st.info("No results to display. Please run a search.")


if __name__ == "__main__":
    # Note: asyncio.run() is typically not used directly inside Streamlit scripts in this manner
    # for button clicks, as Streamlit manages its own execution flow.
    # The asyncio.run() calls within the "Search Companies" button click handler are
    # specific to executing the async functions from related_companies.py.
    show() 