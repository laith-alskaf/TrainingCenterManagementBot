# Training Center Management Platform

A production-ready Training Center Management Platform with multilingual Telegram Bot (Arabic + English), Google Drive, Google Sheets, and Meta Graph API integrations.

## Features

- 📚 Course and student management via Telegram Bot
- 🌍 Multilingual support (Arabic + English)
- 📁 Google Drive integration for course materials
- 📊 Google Sheets integration for scheduled posts
- 📱 Auto-publishing to Facebook and Instagram
- ⏰ Scheduler with Syria timezone (Asia/Damascus)

## Architecture

This project follows **Clean Architecture** with SOLID principles:

```
src/
├── domain/          # Core business entities & interfaces
├── application/     # Use cases & business logic
├── infrastructure/  # External implementations (DB, APIs, Bot)
└── presentation/    # Entry points & DI container
```

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python src/main.py`

## Environment Variables

See `.env.example` for all required configuration.

## Google Sheets Format

| content | image_url | date | time | platform | status |
|---------|-----------|------|------|----------|--------|
| Post text | https://... | 2024-01-15 | 14:30 | facebook | pending |

- **date**: YYYY-MM-DD in Syria time
- **time**: HH:MM 24-hour in Syria time
- **platform**: `facebook`, `instagram`, or `both`
- **status**: `pending` or `published`

## License

MIT
