import streamlit as st
from style_utils import apply_sidebar_styles

st.set_page_config(
    page_title="AI Sandbox",
    layout="wide",
    page_icon="https://fonts.gstatic.com/s/i/materialicons/search/v6/24px.svg"
)
apply_sidebar_styles()


st.logo("https://www.mcoapp.org/ed54bbfbcf85d2b60374.png")
    
    
# Define the content for the home page
def home_page():
    st.title("AI Sandbox: Experimental Features Showcase")
    st.markdown("""
    Welcome to the **AI Sandbox**! 

    This platform showcases experimental AI-powered features developed for exploration and feedback. Currently, it includes:

    *   **Market Research:** Search for companies using OpenAI (Gemini and Perplexity will be added in the future). Input a single company name or upload a CSV/Excel file with a list of companies. If a file is uploaded, you can specify the column containing company names.
    
    Use the sidebar to navigate and interact with the available features. Your feedback is valuable for refining these experimental tools.
    """)


# Run the navigation
pg = st.navigation(
    {
        "AI Sandbox": [st.Page(home_page, title="Home", icon="🏠", default=True)],
        "Market Research": [
            st.Page("pages/market_research/search.py", title="Search", icon="🔬", url_path="mr_search"), # Using a generic search icon as an example
            # st.Page("pages/market_research/results.py", title="View Results", icon="📰", url_path="mr_results"),
            st.Page("pages/market_research/faq.py", title="FAQ", icon="❓", url_path="mr_faq"),
        ]
    },
    expanded=True
)
pg.run()