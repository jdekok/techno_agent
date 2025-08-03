# Amsterdam Techno Event Aggregator 🎵

Automatically discover techno events in Amsterdam by scraping venue websites weekly.

## Features

- Scrapes multiple Amsterdam techno venues (Shelter, Radion, Lofi)
- Filters for techno-specific events
- Sends weekly email summaries
- Runs automatically via GitHub Actions
- Supports manual triggers

## Setup

### 1. Configure GitHub Secrets

Go to Settings → Secrets and add:

- `SMTP_SERVER`: Your SMTP server (e.g., `smtp.gmail.com`)
- `SMTP_PORT`: SMTP port (e.g., `587`)
- `SMTP_USERNAME`: Your email username
- `SMTP_PASSWORD`: Your email password/app password
- `SMTP_FROM_EMAIL`: From email address
- `DEFAULT_EMAIL_RECIPIENT`: Default recipient for automated runs

### 2. Enable GitHub Actions

The workflow runs automatically every Monday at 10 AM UTC. You can also trigger it manually from the Actions tab.

### 3. External Trigger (Optional)

For extra reliability, set up a webhook trigger using cron-job.org:

1. Go to [cron-job.org](https://cron-job.org)
2. Create a new cron job
3. Set URL: `https://api.github.com/repos/YOUR_USERNAME/techno_agent/dispatches`
4. Method: POST
5. Headers:
   ```
   Authorization: token YOUR_GITHUB_TOKEN
   Accept: application/vnd.github.v3+json
   Content-Type: application/json
   ```
6. Body:
   ```json
   {"event_type": "scrape-events"}
   ```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run scraper (JSON output)
python main.py

# Run with email
python main.py --email your@email.com --output email

# Look ahead 14 days
python main.py --days 14
```

## Adding New Venues

1. Create a new scraper in `scrapers/` inheriting from `BaseScraper`
2. Implement the `scrape_events()` method
3. Add the scraper to `main.py`

## Venues Currently Tracked

- **Shelter** - Underground club under A'DAM Tower
- **Radion** - Multi-space arts and music venue  
- **Lofi** - Industrial venue with multiple dancefloors

## Future Enhancements

- More venues (Garage Noord, Doka, Sexyland)
- Instagram scraping for pop-up events
- Telegram channel integration
- Event categorization by subgenre