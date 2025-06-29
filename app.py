# app.py
# Final version with 1-hour cache and improved UI layout.

import time
import pyotp
import pandas as pd
import streamlit as st
import pytz # Import the pytz library for timezone handling
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="My Portfolio Dashboard",
    page_icon="💹",
    layout="wide"
)

# --- Function to load secrets ---
def get_credentials(secret_name):
    try:
        # Running on Streamlit Cloud, get secrets from st.secrets
        return st.secrets[secret_name]
    except (FileNotFoundError, KeyError):
        # Running locally, get secrets from config.py
        print("Running in local mode. Loading credentials from config.py")
        from config import API_KEY, API_SECRET, USER_ID, PASSWORD, TOTP_KEY, APP_PASSWORD
        
        creds_local = {
            "API_KEY": API_KEY,
            "API_SECRET": API_SECRET,
            "USER_ID": USER_ID,
            "PASSWORD": PASSWORD,
            "TOTP_KEY": TOTP_KEY,
            "APP_PASSWORD": APP_PASSWORD
        }
        return creds_local[secret_name]

def check_password():
    """Returns `True` if the user had a correct password."""
    if st.session_state.get("password_correct", False):
        return True
    
    def password_entered():
        if st.session_state["password"] == get_credentials("APP_PASSWORD"):
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

# --- CHANGE 1: REFRESH EVERY HOUR ---
@st.cache_data(ttl=3600)
def get_holdings_data():
    """Connects to Zerodha, gets holdings, and returns a DataFrame."""
    print(f"--- Running data fetch at {datetime.now()} ---")
    
    try:
        kite = KiteConnect(api_key=get_credentials("API_KEY"))
        login_url = kite.login_url()
        service = Service() 
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(login_url)
            wait = WebDriverWait(driver, 20)
            
            user_id_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
            user_id_field.send_keys(get_credentials("USER_ID"))
            password_field = driver.find_element(By.ID, "password")
            password_field.send_keys(get_credentials("PASSWORD"))
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(2)
            
            totp_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
            totp = pyotp.TOTP(get_credentials("TOTP_KEY")).now()
            totp_field.send_keys(totp)

            wait.until(EC.url_contains("request_token"))
            request_token = driver.current_url.split("request_token=")[1].split("&")[0]
            
            data = kite.generate_session(request_token, api_secret=get_credentials("API_SECRET"))
            kite.set_access_token(data["access_token"])
        
        holdings = kite.holdings()
        return pd.DataFrame(holdings)

    except Exception as e:
        st.error(f"An error occurred during data fetching: {e}")
        return pd.DataFrame()

# --- Main App UI ---
st.title("My Personal Portfolio Dashboard")

if check_password():
    # --- CHANGE 2: MOVED REFRESH BUTTON AND TIMESTAMP TO THE TOP ---
    col1, col2 = st.columns([4, 1]) # Create columns to align items
    
    with col1:
        # Get the current time in the Asia/Kolkata timezone
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        st.info(f"Last updated: {now_ist.strftime('%d-%b-%Y, %I:%M %p IST')}")

    with col2:
        if st.button('Refresh Data Now'):
            st.cache_data.clear()
            st.rerun()
    
    # Add a little space
    st.markdown("---") 

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
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        sum_col1.metric("Total Investment", f"₹{total_invested:,.2f}")
        sum_col2.metric("Current Value", f"₹{total_current_value:,.2f}")
        sum_col3.metric("Overall P&L", f"₹{overall_pnl:,.2f}", f"{overall_pnl_percent:.2f}%")
        
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
        
    else:
        st.warning("Could not retrieve portfolio data. Please try refreshing.")
