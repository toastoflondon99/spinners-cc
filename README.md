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
- Database: SQLite (in /tmp)

## Structure
```
public/          # Static frontend files
  index.html
  base.css
  style.css
  app.js
api/             # Vercel serverless Python functions
  index.py       # All API routes
vercel.json      # Routing config
```

## Note
SQLite on Vercel uses `/tmp` which is ephemeral — data resets between cold starts. For persistent data, consider upgrading to Vercel Postgres or Turso.
