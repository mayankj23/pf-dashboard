# scheduler.py
# This script's only job is to send a push notification.
# It will be run by GitHub Actions on a schedule.

import os
import requests
import sys

def send_notification():
    """Sends a push notification via the IFTTT webhook."""
    
    # Get the webhook URL from GitHub Actions secrets
    ifttt_webhook_url = os.environ.get("IFTTT_WEBHOOK_URL")
    
    if not ifttt_webhook_url:
        print("Error: IFTTT_WEBHOOK_URL secret not found.")
        sys.exit(1) # Exit with an error code
        
    try:
        print(f"Triggering IFTTT webhook...")
        response = requests.post(ifttt_webhook_url)
        response.raise_for_status() # This will raise an error for bad responses (4xx or 5xx)
        print("Notification sent successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification: {e}")
        sys.exit(1) # Exit with an error code

if __name__ == "__main__":
    send_notification()
