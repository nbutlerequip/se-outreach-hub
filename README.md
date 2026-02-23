# SE Customer Outreach Hub

Five campaigns. One app. Call log saved to Google Sheets.

## Campaigns

| Campaign | Targets | Source |
|----------|---------|--------|
| Recovery | 912 | Declining existing customers, 50 per branch |
| Conquest | 1,226 | SN Match (529 warm) + EDA Tier A (697 cold) |
| Parts Campaign | 1,700 | Seasonal parts buyers by category |
| Service Seasonality | 4,628 | Service customers by month |
| Consignment | 221 | High-frequency filter/wear part buyers |

## Google Sheets Setup (3 steps)

### Step 1: Create a Google Sheet
Create a new Google Sheet. Name it whatever you want. Copy the URL.

### Step 2: Share with your service account
Share the Google Sheet with your service account email
(looks like: something@project-name.iam.gserviceaccount.com)
Give it **Editor** access.

### Step 3: Add Streamlit Secrets
In Streamlit Cloud, go to your app → Settings → Secrets, and paste:

```toml
sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-service@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service%40your-project.iam.gserviceaccount.com"
```

The app auto-creates a "call_log" worksheet with headers on first run.

## Fallback
If Google Sheets is not configured, the app falls back to local JSON storage.
The login page shows connection status so you can verify.

## Files
- `app.py` - Main application
- `data_*.csv` - Campaign data files (6 files)
- `requirements.txt` - Dependencies (streamlit, pandas, gspread, google-auth)

Created by Nick Butler - Southeastern Equipment - 2026
