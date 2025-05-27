import streamlit as st

def show():
    st.title("Frequently Asked Questions (FAQ) - Company Search")

    st.header("About the Company Search")
    st.subheader("Q: What is the Company Search page for?")
    st.write("A: This page helps you discover companies based on specific capabilities, an optional seed company example, and geographic focus (region or country). It uses AI (powered by OpenAI) to find and analyze company information from the web.")

    st.subheader("Q: Which AI or search engines are used for finding companies?")
    st.write("A: The company search and analysis functionalities primarily leverage OpenAI's capabilities for web searching and information processing.")

    st.header("How to Define Your Search")
    st.subheader("Q: How do I specify what kind of companies I'm looking for?")
    st.write("""
    A: You can define your search criteria in several ways:
    *   **Capabilities:** Directly enter a list of capabilities (e.g., 'cybersecurity', 'AI ethics', 'renewable energy technology'). These describe the expertise or services of the companies you want to find.
    *   **Seed Company (Optional):** Provide the name of a well-known company in your area of interest. The system will analyze this 'seed company' to automatically suggest relevant capabilities for your search.
    *   **Geographic Scope:** Choose to search within a specific 'Country' or a broader 'Region' (like EU, ASEAN, MENA, ASIA(CN/JP/KR)).
    """)

    st.subheader("Q: What if I provide a seed company? How are its capabilities determined?")
    st.write("A: If you provide a seed company, the application uses an AI model to research that company online. It identifies the company's primary business focus, services, and expertise. These identified capabilities are then populated for your search, and you can modify them further.")

    st.subheader("Q: What are the default capabilities if I don't specify any or use a seed company?")
    st.write("A: If no seed company is provided and you don't enter any specific capabilities, the search will use a default set: 'narrative intelligence', 'disinformation detection', 'Information Operations (IO) Defense', and 'inauthentic online behaviour detection'. You can always edit or replace these.")

    st.header("Search Features and Options")
    st.subheader("Q: What is 'Deep Search'?")
    st.write("A: 'Deep Search' is an advanced option for a more thorough investigation. It performs an initial search, then uses AI to analyze those initial results to refine the search query and identify key characteristics of relevant companies. A second, more targeted search is then conducted using these refinements. This process typically yields more comprehensive and relevant results but takes significantly longer.")

    st.subheader("Q: Which regions and countries can I search in?")
    st.write("""
    A:
    *   **Regions:** You can select from pre-defined regions: EU (European Union), ASEAN (Association of Southeast Asian Nations), MENA (Middle East and North Africa), and ASIA(CN/JP/KR) (China, Japan, South Korea).
    *   **Countries:** A dropdown list of supported countries is available for targeted searches.
    """)

    st.header("Understanding and Using Results")
    st.subheader("Q: How are the search results presented?")
    st.write("A: The application displays a summary, including the total number of unique companies found. You'll see a table with company details. If you searched by region, the results will also be broken down by each country within that region. A preview of the top 20 companies is shown directly on the page.")

    st.subheader("Q: Can I download the search results?")
    st.write("A: Yes, you can download the complete list of found companies and their details. The results are available for download in both JSON and Excel (XLSX) formats.")

# To run this page standalone for testing (optional)
if __name__ == "__main__":
    show() 