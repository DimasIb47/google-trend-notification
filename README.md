# Google Trends Gaming Alert System

A 24/7 real-time alert system that monitors **Google Trends "Trending Now"** for gaming topics and sends instant notifications to Discord.

## Features

- 🎮 Monitors **Games category** (id=6) on Google Trends
- 🌍 Tracks **US, GB, and Indonesia** simultaneously
- 🔄 Polls every 60-120 seconds with random jitter
- 🔕 **Per-day deduplication** — same trend won't spam you
- 📢 **Discord notifications** with rich embeds
- 💾 SQLite database for audit trail
- 🏥 Health check endpoint for monitoring
- 🐳 Docker-ready for 24/7 VPS deployment

## Quick Start

### 1. Clone and Configure

```bash
cd google-trend-fetcher
cp .env.example .env
```

Edit `.env` and set your Discord webhook URL:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
```

### 2. Run with Docker (Recommended)

```bash
docker-compose up -d
```

### 3. Run Locally (Development)

```bash
# Install dependencies
pip install -e .

# Run the system
python -m trend_fetcher.main
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_WEBHOOK_URL` | (required) | Discord webhook URL |
| `POLL_INTERVAL_MIN` | `60` | Min poll interval (seconds) |
| `POLL_INTERVAL_MAX` | `120` | Max poll interval (seconds) |
| `GEOS` | `US,GB,ID` | Geo codes to monitor |
| `CATEGORY_ID` | `6` | Google Trends category (6=Games) |
| `HOURS` | `24` | Time window |
| `DATABASE_PATH` | `./data/trends.db` | SQLite path |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /healthz` | Health check (for container orchestration) |
| `GET /stats` | System statistics |
| `GET /ready` | Readiness probe |

## How It Works

1. **Fetcher** — Calls Google Trends internal `batchexecute` API
2. **Parser** — Extracts trend data (title, volume, growth, time)
3. **Deduplicator** — Checks if trend was already seen today
4. **Notifier** — Sends Discord webhook for new trends
5. **Database** — Logs all events for auditing

## Discord Notification Format

```
🔥 Pokemon Perfect Order

📊 Volume: 2K+ (+200%)
⏰ Started: 3 hours ago
⏱️ Duration: Lasted 2 hrs
🟢 Status: Active

📍 Region: 🇮🇩 Indonesia
🏆 Rank: #1
🎮 Category: Games
```

## License

MIT
