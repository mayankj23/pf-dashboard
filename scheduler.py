# scheduler.py
# This script sends a push notification using the nfty.sh service.
# It will be run by GitHub Actions on a schedule.

import os
import requests
import sys

def send_notification():
    """Sends a push notification via the nfty.sh service."""
    
    # Get the secret topic name from GitHub Actions secrets
    nfty_topic = os.environ.get("NFTY_TOPIC")
    dashboard_url = os.environ.get("DASHBOARD_URL")
    
    if not nfty_topic or not dashboard_url:
        print("Error: NFTY_TOPIC or DASHBOARD_URL secret not found.")
        sys.exit(1)
        
    try:
        print(f"Sending notification to nfty.sh topic: {nfty_topic}")
        
        # The message is sent in the body of the request.
        # Headers are used to add a title and specify actions (like a link).
        requests.post(
            f"https://ntfy.sh/{nfty_topic}",
            data="Dad, your daily portfolio report is ready. Tap to view.".encode('utf-8'),
            headers={
                "Title": "Portfolio Report Is Ready",
                "Priority": "default",
                "Tags": "chart_with_upwards_trend",
                "Click": dashboard_url
            }
        )
        
        print("Notification sent successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_notification()
