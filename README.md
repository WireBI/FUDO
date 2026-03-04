# Alex Coffee Analytics Dashboard

A full-stack analytics dashboard for coffee store sales data from the FU.DO POS system. Provides real-time insights across revenue, products, categories, and hourly patterns.

## Stack

- **Frontend**: Next.js 14 + React + Tailwind CSS + Recharts (deployed on Vercel)
- **Backend**: Python FastAPI + SQLAlchemy (deployed on Railway)
- **Database**: Neon PostgreSQL
- **Data Source**: FU.DO General-Purpose API

## Features

### Dashboard Dashboards
- **KPI Overview**: Total revenue, order count, average ticket, items sold with period-over-period comparison
- **Revenue Trend**: Daily revenue time series with area chart
- **Top Products**: Top 10 products by revenue (horizontal bar chart)
- **Sales by Category**: Revenue breakdown by product category (donut chart)
- **Hourly Distribution**: Peak sales hours visualization (bar chart)
- **Recent Transactions**: Latest 20 sales with product, amount, and timestamp

### Settings & Sync
- Manual data sync trigger (pull latest 30 days from FU.DO)
- FU.DO API connection status indicator
- Sync history with status and record counts
- Period filters: Today, This Week, This Month, This Year

### Admin Section
- **Credential Management**: Store and update FU.DO API secrets securely in the database
- **Encrypted Storage**: Secrets are encrypted with Fernet before storage (never stored in plain text)
- **API Key Auth**: Protected with admin API key stored in Railway environment variables
- **Status Tracking**: View credential source (environment or database) and update history
- **No Downtime**: Update API secrets without redeploying the application

## Getting Started

### Prerequisites

1. **FU.DO Account**: Pro Plan with API access enabled
   - Contact `soporte@fu.do` to enable the "API de proposito general"
   - API Secret token (generate in Admin > Users > Establecer API Secret)

2. **Development Tools**:
   - Node.js 18+ (for frontend)
   - Python 3.9+ (for backend)
   - PostgreSQL (or Neon account for cloud database)

3. **Environment Setup**:
   - Vercel account (frontend deployment)
   - Railway account (backend deployment)
   - Neon account (PostgreSQL cluster)

### Local Setup

#### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your credentials:
# FUDO_API_SECRET=your_api_secret_here
# DATABASE_URL=postgresql+asyncpg://...

# Run migrations (tables auto-created on startup)
python -m alembic upgrade head  # (if needed)

# Start the server
uvicorn app.main:app --reload
# Should be available at http://localhost:8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
cp .env.example .env.local
# .env.local should have:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
# Open http://localhost:3000
```

### Initial Data Sync

Once both servers are running:

1. Go to http://localhost:3000/settings
2. Click "Sync Now" to pull the last 30 days of data from FU.DO
3. Dashboard will populate once sync completes
4. Check Settings for sync status and any errors

### Admin Panel (Managing Credentials)

To store and manage your FU.DO API secret securely:

1. Generate a Fernet encryption key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Set environment variables:
   - `ADMIN_API_KEY`: A secure key you create (e.g., `generate $(openssl rand -hex 32)`)
   - `ENCRYPTION_KEY`: The Fernet key generated above

3. Once deployed, visit http://localhost:3000/admin:
   - Enter your admin API key to authenticate
   - Add your FU.DO API secret (it will be encrypted before storage)
   - The secret is never displayed in plain text, only the last 4 characters are visible
   - Update anytime without redeploying your backend

**Why this matters**: If your FU.DO API secret expires, you can update it via the admin panel without redeploying—just go to `/admin`, enter your admin key, paste the new secret, and click "Update Secret".

## API Endpoints

### Dashboard
- `GET /api/dashboard/overview?period={today|week|month|year}` - KPI data
- `GET /api/dashboard/sales-trend?period={period}` - Time series revenue
- `GET /api/dashboard/top-products?period={period}&limit=10` - Top products
- `GET /api/dashboard/sales-by-category?period={period}` - Category breakdown
- `GET /api/dashboard/hourly-distribution?period={period}` - Hourly aggregation
- `GET /api/dashboard/recent-sales?limit=20` - Latest transactions

### Sync & Health
- `POST /api/sync?days_back=30` - Trigger manual sync
- `GET /api/sync/status` - View recent syncs and history
- `GET /api/sync/health` - Check FU.DO API connectivity
- `GET /api/health` - Service health check

### Admin (Protected with X-Admin-Key header)
- `GET /api/admin/credentials` - Get current stored credentials (masked)
- `POST /api/admin/credentials` - Update FU.DO API secret
- `GET /api/admin/credentials/status` - Check credential source and configuration status

## Environment Variables

### Backend (Railway)

```env
# FU.DO API Configuration
FUDO_API_URL=https://api.fu.do
FUDO_API_SECRET=your_fudo_api_secret_here

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname

# Frontend URL (for CORS)
FRONTEND_URL=https://your-vercel-app.vercel.app

# Admin Access (for credential management)
ADMIN_API_KEY=your_secure_admin_key_here

# Encryption Key (Fernet key for storing secrets)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_fernet_encryption_key_here
```

### Frontend (Vercel)

```env
NEXT_PUBLIC_API_URL=https://alex-coffee-api.up.railway.app
```

## Database Schema

### Tables
- `api_credentials` - Encrypted FU.DO API secrets (stored in database for easy updates)
- `categories` - Product categories from FU.DO
- `products` - Product catalog with pricing
- `sales` - Individual sale transactions
- `sync_logs` - Sync operation history and status

## Deployment

### Vercel (Frontend)

```bash
cd frontend
vercel deploy
```

Push to a GitHub repo and connect to Vercel for automatic deploys. Set env var:
```
NEXT_PUBLIC_API_URL=https://alex-coffee-api.up.railway.app
```

### Railway (Backend)

1. Push backend folder to GitHub
2. Create new project on Railway
3. Connect GitHub repo
4. Set environment variables in Railway dashboard:
   ```
   FUDO_API_SECRET=your_token
   DATABASE_URL=postgresql://...
   FRONTEND_URL=https://your-vercel-app.vercel.app
   ADMIN_API_KEY=your_secure_admin_key_here
   ENCRYPTION_KEY=your_fernet_encryption_key_here
   ```
5. Railway auto-deploys on push
6. Generate `ADMIN_API_KEY` and `ENCRYPTION_KEY`:
   - Admin key: Create a random secure string (e.g., `openssl rand -base64 32`)
   - Encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### Neon (PostgreSQL)

1. Create a Neon project at https://neon.tech
2. Copy connection string: `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname`
3. Add `?sslmode=require` to the URL if using Railway
4. Set as `DATABASE_URL` in Railway environment

## FU.DO API Notes

- **API Docs**: https://dev.fu.do/api (interactive Swagger UI)
- **Auth**: API Secret token in Authorization header (expires every 10 days)
- **Data Available**: Sales, products, categories (up to 4 years historical)
- **Rate Limits**: Not explicitly documented; client includes sensible timeout (30s)
- **Endpoints**: Client uses flexible paths (`/v1/sales`, `/v1/products`, etc.)
  - May need adjustment if FU.DO updates their API structure

## FU.DO API Integration Details

The backend client (`app/fudo_client.py`) handles:
- Token-based authentication
- Flexible endpoint discovery (paths can be updated)
- Pagination for large datasets
- Error handling with helpful messages
- Automatic session management

The sync service (`app/sync.py`) performs:
- Category sync (creates/updates categories)
- Product sync (maps to categories)
- Sales sync with nested item handling (supports both flat and nested sales structures)
- Upsert logic (won't create duplicates via fudo_id)
- 10-day rolling historical sync by default

## Troubleshooting

### "API error 401: Invalid or expired API token"
- Your FU.DO API Secret has expired or is invalid
- Generate a new one in FU.DO Admin > Users > {user} > Establecer API Secret
- Update .env and restart backend

### "Connection refused" to database
- Make sure Neon/PostgreSQL is running and accessible
- Check DATABASE_URL is correct (including `?sslmode=require` for Neon)
- Verify firewall/IP allowlisting for Neon

### Dashboard shows no data
- Verify sync completed successfully in Settings
- Check FU.DO connection status indicator
- Ensure you have sales data in your FU.DO account for the selected period

### Graphs are empty
- Check browser console for API errors
- Verify backend is running and reachable
- Try clicking Sync Now to force a refresh

## Architecture Notes

```
Frontend (Vercel)           Backend (Railway)          Database (Neon)
┌──────────────────┐        ┌─────────────────┐        ┌──────────────┐
│  Next.js/React   │◄──────►│  FastAPI        │◄──────►│  PostgreSQL  │
│  shadcn/ui       │ HTTP   │  SQLAlchemy     │ asyncpg│              │
│  Recharts charts │        │  Python         │        │ Tables:      │
└──────────────────┘        └────────┬────────┘        │  - sales     │
                                     │                  │  - products  │
                                     │                  │  - categories│
                            ┌────────▼──────────┐       │  - sync_logs │
                            │  FU.DO API        │       └──────────────┘
                            │  General-Purpose  │
                            └───────────────────┘
```

## Support

For issues with:
- **FU.DO API**: Contact `soporte@fu.do`
- **Frontend/Backend**: Review logs and check configuration
- **Database**: Check Neon console for performance and query logs

## License

This project is for Alex Coffee internal use.
