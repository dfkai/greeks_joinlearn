# Deribit API Setup Guide

This guide walks you through creating Deribit API credentials for the Options Analytics platform.

## Table of Contents

- [Test vs Production Environment](#test-vs-production-environment)
- [Creating a Deribit Account](#creating-a-deribit-account)
- [Generating API Keys](#generating-api-keys)
- [Configuring the Application](#configuring-the-application)
- [Security Best Practices](#security-best-practices)
- [API Rate Limits](#api-rate-limits)
- [Testing Your Credentials](#testing-your-credentials)
- [Troubleshooting](#troubleshooting)

---

## Test vs Production Environment

### Test Environment (Recommended for Learning)

**Use this if you want to:**
- Learn options trading without risk
- Test strategies with paper trading
- Explore the platform features
- Educational purposes

**Characteristics:**
- URL: https://test.deribit.com
- Free test BTC and ETH
- No real money involved
- Identical to production features
- Separate account from production

### Production Environment (Real Trading)

**Use this if you want to:**
- Trade with real money
- Execute actual market orders
- Manage real portfolio

**Characteristics:**
- URL: https://www.deribit.com
- Requires funding with real cryptocurrency
- Real financial risk
- KYC verification required for withdrawals

**⚠️ WARNING**: Only use production after thorough testing in test environment.

---

## Creating a Deribit Account

### For Test Environment (Recommended Start)

1. **Visit Test Platform**
   - Go to https://test.deribit.com
   - Click "Sign Up" in top right

2. **Register Account**
   - Enter email address
   - Create strong password
   - Accept terms and conditions
   - Click "Sign Up"

3. **Verify Email**
   - Check your email inbox
   - Click verification link
   - Log in to test.deribit.com

4. **Get Test Funds**
   - After login, you automatically receive test BTC/ETH
   - No real money required
   - Funds reset periodically

### For Production Environment (Advanced)

1. **Visit Production Platform**
   - Go to https://www.deribit.com
   - Click "Sign Up"

2. **Complete Registration**
   - Provide email and password
   - Verify email address
   - Enable 2FA (highly recommended)

3. **KYC Verification** (for withdrawals)
   - Provide identification documents
   - Wait for approval (1-3 days)

4. **Fund Account**
   - Deposit BTC or ETH
   - Wait for blockchain confirmations

**⚠️ IMPORTANT**: Start with small amounts. Options trading is high-risk.

---

## Generating API Keys

### Step 1: Log Into Deribit

**Test Environment:**
- Go to https://test.deribit.com
- Log in with your credentials

**Production:**
- Go to https://www.deribit.com
- Log in with your credentials

### Step 2: Navigate to API Settings

1. Click your **username** in top right corner
2. Select **"Account"** from dropdown
3. Click **"API"** tab in left sidebar

### Step 3: Create New API Key

1. Click **"Add New Key"** button

2. **Configure API Key:**
   - **Name**: `Options Analytics` (or any descriptive name)
   - **Permissions**: Select **"Read Only"**
     - ✅ Account read
     - ✅ Trading read (for portfolio)
     - ❌ Trading write (NOT needed - safer)
     - ❌ Withdrawal (NEVER enable for read-only apps)

3. **Advanced Settings** (optional):
   - **IP Whitelist**: Add your IP for extra security
   - **Max Requests**: Leave default
   - **Expiration**: Set if desired (e.g., 90 days)

4. Click **"Create"**

### Step 4: Save Credentials

**IMPORTANT**: This is the ONLY time you'll see the secret!

You'll receive:
```
Client ID: 8_chars_here
Client Secret: very_long_string_here
```

**Immediately save these to a secure location:**
- Password manager (recommended)
- Encrypted file
- Secure notes app

**NEVER:**
- ❌ Share publicly
- ❌ Commit to Git
- ❌ Post in Discord/Slack
- ❌ Email unencrypted

---

## Configuring the Application

### Option 1: Local Development

Create `.env` file in project root:

```bash
# Copy example file
cp .env.example .env

# Edit .env
nano .env
```

Add your credentials:

```env
# Deribit API Configuration
DERIBIT_ENV=test

# Test Environment Credentials
DERIBIT_CLIENT_ID_TEST=YourClientID
DERIBIT_CLIENT_SECRET_TEST=YourClientSecret

# Production Environment Credentials (leave empty if not using)
DERIBIT_CLIENT_ID_PROD=
DERIBIT_CLIENT_SECRET_PROD=

# Risk-free rate for Black-Scholes calculations (5% = 0.05)
RISK_FREE_RATE=0.05
```

**File permissions** (important for security):
```bash
chmod 600 .env  # Only you can read/write
```

### Option 2: Streamlit Cloud

1. Go to your app's dashboard at https://share.streamlit.io
2. Click **"Manage app"**
3. Click **"Settings"** → **"Secrets"**
4. Paste your configuration:

```toml
# Deribit API Configuration
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "YourClientID"
DERIBIT_CLIENT_SECRET_TEST = "YourClientSecret"
RISK_FREE_RATE = "0.05"
```

5. Click **"Save"**
6. App will automatically restart

### Option 3: Hugging Face Spaces

1. Create `.streamlit/secrets.toml` in your Space:

```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml <<EOF
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "YourClientID"
DERIBIT_CLIENT_SECRET_TEST = "YourClientSecret"
RISK_FREE_RATE = "0.05"
EOF
```

2. Push to your Space:

```bash
git add .streamlit/secrets.toml
git commit -m "Add API credentials"
git push
```

**NOTE**: Ensure `.streamlit/secrets.toml` is in `.gitignore` if using public repo!

### Option 4: Docker

Create `.env` file:

```bash
cat > .env <<EOF
DERIBIT_ENV=test
DERIBIT_CLIENT_ID_TEST=YourClientID
DERIBIT_CLIENT_SECRET_TEST=YourClientSecret
RISK_FREE_RATE=0.05
EOF
```

Run with environment file:

```bash
docker run --env-file .env -p 8501:8501 greeks-analytics
```

### Option 5: Railway/Render

1. Go to your service dashboard
2. Navigate to **"Environment Variables"** or **"Settings"**
3. Add each variable:
   - `DERIBIT_ENV` = `test`
   - `DERIBIT_CLIENT_ID_TEST` = `YourClientID`
   - `DERIBIT_CLIENT_SECRET_TEST` = `YourClientSecret`
   - `RISK_FREE_RATE` = `0.05`

4. Save and redeploy

---

## Security Best Practices

### 1. Read-Only Permissions

**Always use read-only API keys** for analytics applications:
- ✅ Account read
- ✅ Trading read
- ❌ Trading write
- ❌ Withdrawal

**Why?** If credentials leak, attackers cannot:
- Execute trades
- Withdraw funds
- Modify account settings

### 2. Environment Variables

**NEVER hard-code credentials:**

```python
# ❌ BAD - Hardcoded credentials
client_id = "8_chars_here"
client_secret = "very_long_string"

# ✅ GOOD - Environment variables
import os
client_id = os.getenv("DERIBIT_CLIENT_ID_TEST")
client_secret = os.getenv("DERIBIT_CLIENT_SECRET_TEST")
```

### 3. Git Ignore

Ensure `.env` is in `.gitignore`:

```bash
# Check if .env is ignored
git check-ignore .env
# Should output: .env

# If not, add it
echo ".env" >> .gitignore
echo ".streamlit/secrets.toml" >> .gitignore
```

### 4. IP Whitelisting (Optional)

For production use, whitelist your IP:
1. Go to Deribit API settings
2. Edit your API key
3. Add your server's static IP
4. Save changes

### 5. API Key Rotation

**Rotate keys periodically:**
- Every 90 days for production
- After any security incident
- When team members leave

**How to rotate:**
1. Create new API key
2. Update application configuration
3. Test thoroughly
4. Delete old API key

### 6. Monitor API Usage

**Check API logs regularly:**
1. Log in to Deribit
2. Go to Account → API → Logs
3. Verify:
   - Only expected IPs
   - Only read operations
   - No suspicious activity

---

## API Rate Limits

### Deribit Rate Limits (as of 2024)

**Public Endpoints:**
- 20 requests per second
- No authentication required

**Private Endpoints (with API key):**
- 10 requests per second
- Includes portfolio, positions, orders

**Matching Engine:**
- 50 requests per second
- For placing/canceling orders

### Handling Rate Limits

The application automatically handles rate limits with:

1. **Request throttling**: Delays between API calls
2. **Exponential backoff**: Retries on rate limit errors
3. **Batch requests**: Combines multiple queries

**If you see rate limit errors:**

```
RateLimitError: Too many requests
```

**Solutions:**
- Wait 1-2 seconds between manual data refreshes
- Reduce polling frequency in monitoring
- Use batch fetching instead of individual requests

### Monitoring Your Usage

Check current rate limit status:

```python
# In Streamlit app, temporarily add:
import streamlit as st
from api.Deribit_HTTP import DeribitAPI

api = DeribitAPI()
# API returns rate limit info in headers
st.write("Rate limit remaining:", api.rate_limit_remaining)
```

---

## Testing Your Credentials

### Quick Test in Application

1. **Start the application:**
   ```bash
   streamlit run app.py
   ```

2. **Check connection status:**
   - Look for green "Connected" indicator in sidebar
   - Should show your account info

3. **Fetch data:**
   - Click "Fetch Fresh Data" in sidebar
   - Wait for completion (30-60 seconds)
   - Verify data appears in views

### Manual Test Script

Create `test_credentials.py`:

```python
import os
from dotenv import load_dotenv
from api.Deribit_HTTP import DeribitAPI

# Load environment variables
load_dotenv()

# Initialize API
api = DeribitAPI(
    env=os.getenv("DERIBIT_ENV", "test"),
    client_id=os.getenv("DERIBIT_CLIENT_ID_TEST"),
    client_secret=os.getenv("DERIBIT_CLIENT_SECRET_TEST")
)

# Test connection
try:
    # Get account summary
    result = api.get_account_summary(currency="BTC")
    print("✅ API Connection Successful!")
    print(f"Account Balance: {result.get('equity', 'N/A')} BTC")

    # Get instruments
    instruments = api.get_instruments(currency="BTC", kind="option")
    print(f"✅ Found {len(instruments)} BTC options")

except Exception as e:
    print(f"❌ API Connection Failed: {e}")
    print("\nTroubleshooting:")
    print("1. Verify credentials in .env file")
    print("2. Check DERIBIT_ENV is 'test' or 'prod'")
    print("3. Ensure API key has 'read' permissions")
```

Run test:

```bash
python test_credentials.py
```

Expected output:

```
✅ API Connection Successful!
Account Balance: 10.0 BTC
✅ Found 847 BTC options
```

---

## Troubleshooting

### Error: "Authentication failed"

**Possible causes:**

1. **Wrong credentials**
   - Verify Client ID and Secret
   - Check for extra spaces
   - Ensure you copied complete secret

2. **Wrong environment**
   - Test credentials won't work with `DERIBIT_ENV=prod`
   - Production credentials won't work with `DERIBIT_ENV=test`

3. **API key deleted**
   - Check if key still exists in Deribit account
   - Create new key if necessary

**Solution:**
```bash
# Verify environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'ENV: {os.getenv(\"DERIBIT_ENV\")}, ID: {os.getenv(\"DERIBIT_CLIENT_ID_TEST\")}')"
```

### Error: "Rate limit exceeded"

**Solution:**
- Wait 60 seconds
- Reduce request frequency
- Use batch operations

### Error: "Insufficient permissions"

**Solution:**
1. Go to Deribit → Account → API
2. Edit your key
3. Enable required permissions:
   - Account read
   - Trading read
4. Save changes
5. Restart application

### Error: "Invalid client credentials"

**Possible causes:**
- API key expired
- IP whitelist excludes your current IP
- Key was revoked

**Solution:**
1. Create new API key
2. Update application configuration
3. Test again

### Data Not Appearing

**Possible causes:**
- First run (no data fetched yet)
- API timeout
- Network issues

**Solution:**
```bash
# Test API connectivity
curl https://test.deribit.com/api/v2/public/test

# Should return: {"jsonrpc":"2.0","result":{"version":"2.0.0"},"usIn":...}
```

---

## Next Steps

After successfully setting up API credentials:

1. ✅ Return to [DEPLOYMENT.md](DEPLOYMENT.md) to complete deployment
2. ✅ Run the application locally to verify everything works
3. ✅ Explore the 8 analysis views
4. ✅ Try building a sample portfolio
5. ✅ Review security settings periodically

**Need Help?**
- Check [Deribit API Documentation](https://docs.deribit.com)
- Review [Troubleshooting section](#troubleshooting)
- Open an issue on GitHub

---

## Additional Resources

### Official Documentation
- [Deribit API Docs](https://docs.deribit.com)
- [Authentication Guide](https://docs.deribit.com/#authentication)
- [Rate Limits](https://docs.deribit.com/#rate-limits)

### Security Resources
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [Environment Variables Best Practices](https://12factor.net/config)

### Community
- [Deribit Insights](https://insights.deribit.com)
- [Trading Discord](https://discord.gg/deribit)

---

**Ready to deploy?** Head back to [DEPLOYMENT.md](DEPLOYMENT.md) 🚀
