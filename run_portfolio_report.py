# run_portfolio_report.py
# This single script automates the entire process:
# 1. Logs into Kite using Selenium and TOTP.
# 2. Generates an access token.
# 3. Fetches and displays the portfolio holdings.

import time
import pyotp
import pandas as pd
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Import credentials from your config file
from config import API_KEY, API_SECRET, USER_ID, PASSWORD, PIN, TOTP_KEY

def get_access_token():
    """
    Automates the Kite login process to get an access_token.
    Returns the access_token string if successful, otherwise returns None.
    """
    print("Starting automated login to get access token...")
    
    kite = KiteConnect(api_key=API_KEY)
    login_url = kite.login_url()

    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=service, options=options)
    access_token = None

    try:
        driver.get(login_url)
        wait = WebDriverWait(driver, 10)

        # Enter User ID and Password
        print("Entering credentials...")
        user_id_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
        user_id_field.send_keys(USER_ID)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(PASSWORD)
        
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Enter TOTP
        print("Entering TOTP...")
        time.sleep(1)
        
        totp_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
        totp = pyotp.TOTP(TOTP_KEY).now()
        totp_field.send_keys(totp)

        # Wait for redirect and capture the request_token
        print("Waiting for redirect...")
        wait.until(EC.url_contains("request_token"))
        
        request_token_url = driver.current_url
        request_token = request_token_url.split("request_token=")[1].split("&")[0]
        print("Request token captured.")

        # Generate the access token
        print("Generating access token...")
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        access_token = data["access_token"]
        print("Access token generated successfully.")

    except Exception as e:
        print(f"An error occurred during login: {e}")
        driver.save_screenshot("error_screenshot.png")
        print("An error screenshot has been saved.")
    finally:
        driver.quit()
        return access_token

def fetch_portfolio(access_token):
    """
    Fetches and displays portfolio holdings using a given access_token.
    """
    if not access_token:
        print("Could not fetch portfolio because the access token is missing.")
        return

    print("\nFetching portfolio holdings...")
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(access_token)

    try:
        holdings = kite.holdings()
        holdings_df = pd.DataFrame(holdings)
        
        if not holdings_df.empty:
            cols_to_show = [
                'tradingsymbol', 'quantity', 'average_price',
                'last_price', 'pnl', 'day_change', 'day_change_percentage'
            ]
            
            for col in cols_to_show:
                if col not in holdings_df.columns:
                    holdings_df[col] = 0

            final_df = holdings_df[cols_to_show].round(2)

            print("--- Your Portfolio Holdings ---")
            print(final_df)
        else:
            print("You have no holdings in your portfolio.")

    except Exception as e:
        print(f"An error occurred while fetching holdings: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Step 1: Get the access token through automation
    token = get_access_token()
    
    # Step 2: Use the token to fetch the portfolio
    fetch_portfolio(token)

