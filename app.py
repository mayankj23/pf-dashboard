# app.py
# Final version for deployment with a fix for the ChromeDriver version mismatch.

import time
import pyotp
import pandas as pd
import streamlit as st
import requests
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service # Keep this import
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager # <-- CHANGE 1: We no longer need this library.

from datetime import datetime
from config import API_KEY, API_SECRET, USER_ID, PASSWORD, PIN, TOTP_KEY # This will be used for local testing

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="My Portfolio Dashboard",
    page_icon="💹",
    layout="wide"
)

# --- Secrets Management and Password Protection ---
def check_password():
    """Returns `True` if the user had a correct password."""
    if st.session_state.get("password_correct", False):
        return True
    
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
            
    st.text_input(
        "Enter Password to View Dashboard", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state and not st.session_state.password_correct:
        st.error("😕 Password incorrect")
    return False

# --- IFTTT Notification Function ---
# This part remains the same.

# --- Data Fetching Logic (Cached) ---
@st.cache_data(ttl=14400)
def get_holdings_data():
    """Connects to Zerodha, gets holdings, and returns a DataFrame."""
    print(f"--- Running data fetch at {datetime.now()} ---")
    
    api_key = st.secrets["API_KEY"]
    api_secret = st.secrets["API_SECRET"]
    user_id = st.secrets["USER_ID"]
    password = st.secrets["PASSWORD"]
    totp_key = st.secrets["TOTP_KEY"]

    try:
        kite = KiteConnect(api_key=api_key)
        login_url = kite.login_url()
        
        # --- CHANGE 2: Simplified Selenium setup ---
        # We now let Selenium's own manager handle the driver automatically.
        # This is more robust in cloud environments.
        service = Service() 
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        
        with webdriver.Chrome(service=service, options=options) as driver:
            # The rest of the Selenium logic is identical
            driver.get(login_url)
            wait = WebDriverWait(driver, 20) # Increased wait time for cloud environment
            
            user_id_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
            user_id_field.send_keys(user_id)
            password_field = driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(2) # Increased sleep time
            
            totp_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
            totp = pyotp.TOTP(totp_key).now()
            totp_field.send_keys(totp)

            wait.until(EC.url_contains("request_token"))
            request_token = driver.current_url.split("request_token=")[1].split("&")[0]
            
            data = kite.generate_session(request_token, api_secret=api_secret)
            kite.set_access_token(data["access_token"])
        
        holdings = kite.holdings()
        return pd.DataFrame(holdings)

    except Exception as e:
        st.error(f"An error occurred during data fetching: {e}")
        return pd.DataFrame()

# --- Main App UI (This part remains the same) ---
st.title("My Personal Portfolio Dashboard")

if check_password():
    holdings_df = get_holdings_data()
    
    if not holdings_df.empty:
        # Calculations...
        holdings_df['invested_value'] = holdings_df['average_price'] * holdings_df['quantity']
        holdings_df['current_value'] = holdings_df['last_price'] * holdings_df['quantity']
        total_invested = holdings_df['invested_value'].sum()
        total_current_value = holdings_df['current_value'].sum()
        overall_pnl = total_current_value - total_invested
        overall_pnl_percent = (overall_pnl / total_invested) * 100 if total_invested > 0 else 0

        # Display UI...
        st.header("Portfolio Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investment", f"₹{total_invested:,.2f}")
        col2.metric("Current Value", f"₹{total_current_value:,.2f}")
        col3.metric("Overall P&L", f"₹{overall_pnl:,.2f}", f"{overall_pnl_percent:.2f}%")
        
        st.header("Individual Holdings")
        cols_to_show = [
            'tradingsymbol', 'quantity', 'average_price', 'last_price', 
            'invested_value', 'current_value', 'pnl', 'day_change_percentage'
        ]
        display_df = holdings_df[cols_to_show].round(2)
        display_df.rename(columns={
            'tradingsymbol': 'Stock', 'quantity': 'Qty', 'average_price': 'Avg. Price',
            'last_price': 'Last Price', 'invested_value': 'Invested', 'current_value': 'Current',
            'pnl': 'P&L', 'day_change_percentage': "Day's Change %"
        }, inplace=True)

        st.dataframe(display_df, use_container_width=True)
        st.info(f"Last updated: {datetime.now().strftime('%d-%b-%Y, %I:%M %p')}")
        
        if st.button('Refresh Data Now (clears cache)'):
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("Could not retrieve portfolio data. Please try refreshing.")
