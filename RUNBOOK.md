# Runbook — Google Trends Gaming Alert System

## Deployment

### First-Time Deploy

```bash
# 1. Clone repository to VPS
git clone <repo-url> /opt/google-trends-gaming
cd /opt/google-trends-gaming

# 2. Configure environment
cp .env.example .env
nano .env  # Set DISCORD_WEBHOOK_URL

# 3. Build and start
docker-compose up -d --build

# 4. Verify
docker-compose logs -f
curl http://localhost:8080/healthz
```

### Update/Redeploy

```bash
cd /opt/google-trends-gaming
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Verify
docker-compose logs --tail=50
```

### Rollback

```bash
# Check previous images
docker images | grep trend-fetcher

# Rollback to specific commit
git checkout <commit-hash>
docker-compose down
docker-compose up -d --build
```

## Operations

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Filter by pattern
docker-compose logs | grep "New trend"
```

### Check Status

```bash
# Health check
curl http://localhost:8080/healthz

# Statistics
curl http://localhost:8080/stats

# Container status
docker-compose ps
```

### Restart

```bash
# Graceful restart
docker-compose restart

# Full restart
docker-compose down
docker-compose up -d
```

### Stop

```bash
docker-compose down
```

## Troubleshooting

### No Notifications

1. Check Discord webhook URL in `.env`
2. Test webhook manually:
   ```bash
   curl -X POST "YOUR_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"content": "Test"}'
   ```
3. Check logs for errors:
   ```bash
   docker-compose logs | grep -i discord
   ```

### Rate Limiting

If you see "Rate limited" in logs:
- Google is throttling requests
- System auto-handles with exponential backoff
- Consider increasing `POLL_INTERVAL_MIN`

### Database Issues

```bash
# Access database
sqlite3 data/trends.db

# Check tables
.tables

# Count trends
SELECT geo, COUNT(*) FROM trends_events GROUP BY geo;

# Check dedupe keys
SELECT COUNT(*) FROM dedupe_keys WHERE expires_at > datetime('now');
```

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Monitoring

### Set Up Uptime Monitoring

Add to your monitoring tool (e.g., UptimeRobot, Healthchecks.io):

- **URL:** `http://YOUR_VPS_IP:8080/healthz`
- **Interval:** 5 minutes
- **Alert on:** Non-200 response or timeout

### Log Aggregation

Logs are JSON-structured. Example log entry:
```json
{"time": "2026-01-09T01:30:00", "level": "INFO", "message": "New trend detected: Pokemon (ID)"}
```

## Backup

### Database Backup

```bash
# Manual backup
cp data/trends.db data/trends.db.backup

# Automated daily backup (add to crontab)
0 0 * * * cp /opt/google-trends-gaming/data/trends.db /backups/trends_$(date +\%Y\%m\%d).db
```

### Configuration Backup

```bash
cp .env .env.backup
```
