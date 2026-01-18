# Deployment Guide

This guide explains how to deploy the Deribit Options Analytics platform to various cloud services.

## Table of Contents

- [Why Vercel Won't Work](#why-vercel-wont-work)
- [Recommended: Streamlit Cloud](#recommended-streamlit-cloud)
- [Alternative: Hugging Face Spaces](#alternative-hugging-face-spaces)
- [Alternative: Railway](#alternative-railway)
- [Alternative: Render](#alternative-render)
- [Self-Hosting with Docker](#self-hosting-with-docker)
- [Environment Variables Reference](#environment-variables-reference)
- [Troubleshooting](#troubleshooting)

---

## Why Vercel Won't Work

**Vercel CANNOT deploy Streamlit applications.** Here's why:

### Architecture Incompatibility

| Requirement | Streamlit Needs | Vercel Provides |
|------------|-----------------|-----------------|
| **Runtime** | Long-running Python process | Serverless functions (max 10s on free tier) |
| **WebSocket** | Required for interactive UI | Limited/no support |
| **State** | Stateful session management | Stateless functions |
| **Framework** | Python web framework | Next.js/React static sites + Node.js functions |

### Why This Matters

- **Streamlit runs as a persistent server** that maintains WebSocket connections for real-time UI updates
- **Vercel is designed for serverless functions** that execute and terminate quickly
- **Python support on Vercel** is only for short-lived API endpoints, not web applications

### Platforms That Won't Work

- ❌ **Vercel** - Serverless functions only
- ❌ **Netlify** - Static sites and functions only
- ❌ **GitHub Pages** - Static HTML only
- ❌ **Cloudflare Pages** - Static sites only

### ✅ What Works Instead

Use platforms designed for **persistent Python web applications**:
- Streamlit Cloud (recommended - 5 minutes)
- Hugging Face Spaces
- Railway
- Render
- Docker on any VPS

---

## Recommended: Streamlit Cloud

**Deployment Time: 5 minutes**
**Cost: FREE for public repos**
**Best For: Quick demos, education, prototypes**

### Prerequisites

- GitHub account
- Public GitHub repository with this code
- Deribit API credentials ([setup guide](API_SETUP.md))

### Step-by-Step Deployment

#### 1. Push Code to GitHub

```bash
# If you haven't already
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/greeks-analytics.git
git push -u origin main
```

**Important**: Repository must be **public** for free Streamlit Cloud deployment.

#### 2. Deploy to Streamlit Cloud

1. Visit [share.streamlit.io](https://share.streamlit.io)
2. Click **"Sign in with GitHub"**
3. Click **"New app"**
4. Configure:
   - **Repository**: Select `YOUR_USERNAME/greeks-analytics`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **"Advanced settings..."**

#### 3. Configure Secrets

In the Secrets section, paste:

```toml
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "your_client_id_here"
DERIBIT_CLIENT_SECRET_TEST = "your_secret_here"
RISK_FREE_RATE = "0.05"
```

**Security Note**: Never commit these values to Git. Streamlit Cloud encrypts secrets.

#### 4. Deploy

1. Click **"Deploy!"**
2. Wait 2-3 minutes for build
3. Your app will be live at: `https://YOUR_USERNAME-greeks-analytics.streamlit.app`

### Managing Your App

- **View logs**: Click "Manage app" → "Logs"
- **Update code**: Push to GitHub → Auto-deploys in 1-2 minutes
- **Update secrets**: "Manage app" → "Settings" → "Secrets"
- **Reboot app**: "Manage app" → "Reboot"

### Limitations

**Free Tier:**
- 1 GB RAM
- Unlimited public apps
- 1 private app only
- Auto-sleep after inactivity (wakes on visit)

**Paid Tier ($20/month):**
- Unlimited private apps
- More resources
- Custom domains

---

## Alternative: Hugging Face Spaces

**Deployment Time: 10 minutes**
**Cost: FREE**
**Best For: Research projects, academic collaboration**

### Why Choose HF Spaces?

- Free GPU support (for future ML features)
- Built-in version control
- Academic community focused
- Permanent hosting (no auto-sleep)

### Prerequisites

- Hugging Face account
- Git installed locally

### Deployment Steps

#### 1. Create a Space

1. Visit [huggingface.co/new-space](https://huggingface.co/new-space)
2. Configure:
   - **Name**: `greeks-analytics`
   - **License**: MIT
   - **SDK**: Streamlit
   - **Hardware**: CPU basic (free)
   - **Visibility**: Public or Private

#### 2. Clone and Push

```bash
# Clone your new space
git clone https://huggingface.co/spaces/YOUR_USERNAME/greeks-analytics
cd greeks-analytics

# Copy your code
rsync -av /path/to/greeks-analytics/ ./ --exclude='.git'

# Add secrets file
cat > .streamlit/secrets.toml <<EOF
DERIBIT_ENV = "test"
DERIBIT_CLIENT_ID_TEST = "your_client_id"
DERIBIT_CLIENT_SECRET_TEST = "your_secret"
RISK_FREE_RATE = "0.05"
EOF

# Push
git add .
git commit -m "Initial deployment"
git push
```

#### 3. Wait for Build

- Build typically takes 3-5 minutes
- Monitor at: `https://huggingface.co/spaces/YOUR_USERNAME/greeks-analytics`

### Managing Your Space

- **Update code**: Push to Git → Auto-rebuilds
- **View logs**: Click "Logs" tab in Space UI
- **Settings**: Click "Settings" in Space UI

---

## Alternative: Railway

**Deployment Time: 15 minutes**
**Cost: $5/month free credit**
**Best For: Professional deployments, custom domains**

### Why Choose Railway?

- Professional-grade infrastructure
- Automatic HTTPS
- Custom domains
- Better performance than free tiers
- Generous free credit

### Prerequisites

- Railway account ([railway.app](https://railway.app))
- GitHub repository

### Deployment Steps

#### 1. Create Project

1. Visit [railway.app/new](https://railway.app/new)
2. Click "Deploy from GitHub repo"
3. Select `greeks-analytics`
4. Railway auto-detects Python/Streamlit

#### 2. Configure Environment

In Railway dashboard:

1. Click your service
2. Go to "Variables" tab
3. Add:
   ```
   DERIBIT_ENV=test
   DERIBIT_CLIENT_ID_TEST=your_client_id
   DERIBIT_CLIENT_SECRET_TEST=your_secret
   RISK_FREE_RATE=0.05
   PORT=8501
   ```

#### 3. Configure Start Command

1. Go to "Settings" tab
2. Set **Start Command**:
   ```
   streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

#### 4. Deploy

- Railway automatically builds and deploys
- You'll get a URL like: `https://greeks-analytics-production.up.railway.app`

### Custom Domain (Optional)

1. Go to "Settings" → "Domains"
2. Click "Custom Domain"
3. Add your domain and configure DNS

---

## Alternative: Render

**Deployment Time: 15 minutes**
**Cost: FREE (with limitations)**
**Best For: Budget-conscious deployments**

### Prerequisites

- Render account ([render.com](https://render.com))
- GitHub repository

### Deployment Steps

#### 1. Create Web Service

1. Visit [dashboard.render.com](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect GitHub and select `greeks-analytics`

#### 2. Configure Service

- **Name**: `greeks-analytics`
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
- **Plan**: Free

#### 3. Add Environment Variables

In "Environment" tab:

```
DERIBIT_ENV=test
DERIBIT_CLIENT_ID_TEST=your_client_id
DERIBIT_CLIENT_SECRET_TEST=your_secret
RISK_FREE_RATE=0.05
```

#### 4. Deploy

- Render builds and deploys automatically
- URL: `https://greeks-analytics.onrender.com`

### Free Tier Limitations

- **Spins down after 15 minutes of inactivity**
- **Cold start takes 30-60 seconds**
- 750 hours/month free (enough for continuous use)

---

## Self-Hosting with Docker

**Setup Time: 30 minutes**
**Cost: Varies by VPS provider**
**Best For: Full control, enterprise deployments**

### Prerequisites

- Docker installed
- VPS or local machine
- Domain name (optional)

### Quick Start

#### 1. Build Image

```bash
cd greeks-analytics
docker build -t greeks-analytics .
```

#### 2. Create Environment File

```bash
cat > .env <<EOF
DERIBIT_ENV=test
DERIBIT_CLIENT_ID_TEST=your_client_id
DERIBIT_CLIENT_SECRET_TEST=your_secret
RISK_FREE_RATE=0.05
EOF
```

#### 3. Run Container

```bash
docker run -d \
  --name greeks-analytics \
  -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  greeks-analytics
```

#### 4. Access Application

- Local: http://localhost:8501
- Remote: http://YOUR_SERVER_IP:8501

### Production Deployment

For production, add **Nginx reverse proxy** with SSL:

#### 1. Create nginx.conf

```nginx
server {
    listen 80;
    server_name analytics.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2. Setup SSL with Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d analytics.yourdomain.com
```

### VPS Recommendations

| Provider | Starting Price | Best For |
|----------|---------------|----------|
| DigitalOcean | $6/month | Ease of use |
| Linode | $5/month | Performance |
| Hetzner | €4.5/month | EU hosting |
| AWS Lightsail | $3.50/month | AWS ecosystem |

---

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DERIBIT_ENV` | Environment (test or prod) | `test` |
| `DERIBIT_CLIENT_ID_TEST` | Test API client ID | `AbCdEfGh` |
| `DERIBIT_CLIENT_SECRET_TEST` | Test API secret | `xyz123...` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `RISK_FREE_RATE` | Risk-free interest rate | `0.05` |
| `DERIBIT_CLIENT_ID_PROD` | Production client ID | - |
| `DERIBIT_CLIENT_SECRET_PROD` | Production secret | - |

### Production vs Test

**Test Environment (Recommended for Learning):**
- Uses testnet.deribit.com
- Paper trading only
- No real money at risk
- Free test BTC/ETH

**Production Environment (Real Trading):**
- Uses www.deribit.com
- Real money trading
- Requires funding account
- Use with caution

---

## Troubleshooting

### Application Won't Start

**Error**: `ModuleNotFoundError: No module named 'streamlit'`

**Solution**: Check `requirements.txt` is present and contains all dependencies.

```bash
# Verify requirements
cat requirements.txt | grep streamlit

# Reinstall
pip install -r requirements.txt
```

### API Connection Fails

**Error**: `Authentication failed`

**Solutions**:

1. Verify credentials in secrets/environment:
   ```python
   # In Streamlit, check:
   import streamlit as st
   st.write(st.secrets)  # Temporarily add this line
   ```

2. Check API key permissions on Deribit:
   - Log in to Deribit testnet
   - Go to Account → API
   - Ensure key has "Read" permissions

3. Verify environment:
   ```bash
   echo $DERIBIT_ENV  # Should be "test" or "prod"
   ```

### Data Not Loading

**Error**: Blank charts or "No data available"

**Solutions**:

1. Click "Fetch Fresh Data" button in sidebar
2. Check Deribit API status: [status.deribit.com](https://status.deribit.com)
3. Verify database permissions:
   ```bash
   ls -la data/
   # Should show options_data.duckdb
   ```

### Streamlit Cloud Timeout

**Error**: `App taking too long to load`

**Solutions**:

1. Check if initial data fetch is too slow
2. Pre-populate database before deploying:
   ```bash
   # Run locally first
   streamlit run app.py
   # Click "Fetch Fresh Data"
   # Commit data/options_data.duckdb to Git
   ```

3. Increase timeout in `.streamlit/config.toml`:
   ```toml
   [server]
   maxUploadSize = 200
   enableXsrfProtection = true
   ```

### Docker Build Fails

**Error**: `ERROR [stage-0 4/6] RUN pip install...`

**Solutions**:

1. Update pip in Dockerfile:
   ```dockerfile
   RUN pip install --upgrade pip
   RUN pip install --no-cache-dir -r requirements.txt
   ```

2. Build with no cache:
   ```bash
   docker build --no-cache -t greeks-analytics .
   ```

### Port Already in Use

**Error**: `OSError: [Errno 48] Address already in use`

**Solutions**:

1. Find process using port 8501:
   ```bash
   lsof -i :8501
   ```

2. Kill the process:
   ```bash
   kill -9 <PID>
   ```

3. Or use a different port:
   ```bash
   streamlit run app.py --server.port=8502
   ```

---

## Getting Help

### Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Deribit API Docs](https://docs.deribit.com)
- [DuckDB Documentation](https://duckdb.org/docs/)

### Common Issues

- **Slow performance**: Free tiers have limited resources. Consider upgrading or self-hosting.
- **API rate limits**: Deribit has rate limits. Add delays between requests if needed.
- **Database locks**: DuckDB is single-writer. Avoid concurrent writes.

### Support

- Open an issue on GitHub
- Check existing issues for solutions
- Review application logs for error details

---

## Next Steps

After successful deployment:

1. ✅ Test all 8 analysis views
2. ✅ Verify data fetching works
3. ✅ Check portfolio builder functionality
4. ✅ Set up monitoring/alerts (if using paid tier)
5. ✅ Configure custom domain (optional)
6. ✅ Review [API_SETUP.md](API_SETUP.md) for security best practices

**Happy Trading!** 📈
