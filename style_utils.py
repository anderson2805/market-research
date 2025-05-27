import streamlit as st

def apply_sidebar_styles():
    # Inject custom CSS for gradient sidebar
    st.markdown("""
    <style>
    [data-testid="stSidebar"] > div:first-child {
        color: #FFFFFF;
        background: linear-gradient(135deg, rgba(9, 123, 150, 0.8) 0%, rgba(6, 37, 146, 0.8) 75.87%);
        background-color: #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True) 