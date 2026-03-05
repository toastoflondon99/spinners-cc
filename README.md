# Spinners CC — Paddington Dads Cycling Club

Web app for the Spinners cycling group training for Tour de Brisbane 2026.

## Features
- Ride tracking & logging
- Personalised training plans (80km or 110km)
- Group leaderboard
- Mt Coot-tha climb tips
- Race day nutrition guide

## Tech
- Frontend: Vanilla HTML/CSS/JS
- Backend: Python serverless functions (Vercel)
- Database: Turso (persistent cloud SQLite) — falls back to local SQLite for dev

## Structure
```
public/          # Static frontend files
  index.html
  base.css
  style.css
  app.js
api/             # Vercel serverless Python functions
  index.py       # All API routes (uses libsql_experimental for Turso)
vercel.json      # Routing config
requirements.txt # Python dependencies
```

## Setup

### 1. Deploy to Vercel
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import the `spinners-cc` GitHub repo
3. Framework preset: **Other**
4. Deploy (it will work but data won't persist yet)

### 2. Set up Turso (persistent database)
1. Go to [turso.tech](https://turso.tech) and sign up (free tier = 500 databases, 9GB storage)
2. Install the Turso CLI:
   ```bash
   curl -sSfL https://get.tur.so/install.sh | bash
   ```
3. Create a database:
   ```bash
   turso db create spinners
   ```
4. Get your database URL:
   ```bash
   turso db show spinners --url
   ```
   It will look like: `libsql://spinners-yourname.turso.io`
5. Create an auth token:
   ```bash
   turso db tokens create spinners
   ```

### 3. Add environment variables in Vercel
1. Go to your Vercel project → **Settings** → **Environment Variables**
2. Add these two:
   - `TURSO_DATABASE_URL` = your database URL from step 4 above
   - `TURSO_AUTH_TOKEN` = your auth token from step 5 above
3. Redeploy (Vercel → Deployments → click the 3 dots on latest → Redeploy)

That's it! Data now persists across deployments and cold starts.

## Local Development
Without the Turso env vars set, the app falls back to a local SQLite database at `/tmp/spinners.db`. Good for testing but data won't persist between restarts.
