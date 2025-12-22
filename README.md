<div align="center">

# 🎓 Training Center Management Platform

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**A comprehensive training center management system with Telegram Bot, payment tracking, and social media automation.**

[Getting Started](#-quick-start) •
[Features](#-features) •
[Architecture](#-architecture) •
[Documentation](#-documentation)

</div>

---

## 📋 Overview

A production-ready platform designed for training centers to manage courses, student registrations, payments, and social media presence — all through a beautiful **Telegram Bot** interface with full **Arabic** and **English** support.

### Key Highlights

- 🤖 **Telegram Bot Interface** - Complete management via intuitive buttons
- 💰 **Payment Tracking** - Detailed payment history with multiple methods
- 📝 **Registration Workflow** - Admin approval system with notifications
- 📱 **Social Media Automation** - Auto-publish to Facebook & Instagram
- 🔔 **Smart Notifications** - Reminders, alerts, and targeted messages

---

## ✨ Features

### For Students
| Feature | Description |
|---------|-------------|
| 📚 Browse Courses | View available courses with details and pricing |
| 📝 Easy Registration | 3-step registration with phone validation |
| 👤 Personal Profile | View registered courses and payment status |
| 🌍 Language Choice | Arabic and English interface |

### For Administrators
| Feature | Description |
|---------|-------------|
| ✅ Approve Registrations | Review and approve/reject student requests |
| 💰 Manage Payments | Track payments with cash, transfer, or card |
| 📢 Send Notifications | Targeted messages to specific students/courses |
| 📣 Broadcast Messages | Send announcements to all users |
| 📤 Upload Materials | Upload files to course-specific Google Drive folders |
| ➕ Create Courses | Multi-step course creation with automatic Drive folder |
| 📊 View Statistics | Student counts and course analytics |

### Automation
| Feature | Description |
|---------|-------------|
| 📅 Scheduled Posts | Auto-publish from Google Sheets |
| ⏰ 24h Reminders | Auto-notify students before course starts |
| 🔄 Payment Updates | Notify students when payment status changes |

---

## 🏗 Architecture

This project follows **Clean Architecture** principles with strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│              (Telegram Handlers, main.py)                   │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│                  (Use Cases, Business Logic)                │
├─────────────────────────────────────────────────────────────┤
│                     Domain Layer                             │
│            (Entities, Interfaces, Value Objects)            │
├─────────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                        │
│         (MongoDB, Google APIs, Telegram, Meta API)          │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
src/
├── domain/                 # Core business logic
│   ├── entities/          # Data models (Course, Student, Registration, etc.)
│   ├── repositories/      # Repository interfaces
│   └── value_objects/     # Phone validation, timezone utils
│
├── application/            # Use cases
│   └── use_cases/         # Business operations
│       ├── use_cases.py           # Core use cases
│       ├── registration_use_cases.py  # Registration & payment
│       └── notification_use_cases.py  # Notifications & reminders
│
├── infrastructure/         # External services
│   ├── adapters/          # Google Drive, Sheets, Meta API
│   ├── database/          # MongoDB connection
│   ├── repositories/      # MongoDB implementations
│   ├── scheduler/         # Post scheduler
│   └── telegram/          # Bot handlers
│       └── handlers/      # All Telegram handlers
│
└── presentation/           # Entry points
    └── container.py       # Dependency injection
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MongoDB Atlas account
- Telegram Bot Token
- Google Cloud Service Account
- (Optional) Meta Graph API credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/training-center-platform.git
cd training-center-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python src/main.py
```

### Environment Variables

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_IDS=123456789,987654321

# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE_NAME=training_center

# Google
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/credentials.json
GOOGLE_DRIVE_FOLDER_ID=folder_id
GOOGLE_SHEETS_ID=spreadsheet_id
GOOGLE_SHEETS_NAME=Sheet1

# Meta (Optional)
META_ACCESS_TOKEN=your_token
META_FACEBOOK_PAGE_ID=page_id
META_INSTAGRAM_ACCOUNT_ID=account_id
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [📘 WORKFLOW.md](WORKFLOW.md) | Complete bot flow simulation and user journeys |
| [📗 SETUP_GUIDE.md](SETUP_GUIDE.md) | Configuration, extension, and customization guide |
| [📙 SERVICES_GUIDE.md](SERVICES_GUIDE.md) | External services setup (Google, Meta, MongoDB) |

---

## 🇸🇾 Syrian Phone Validation

The system validates Syrian phone numbers:

```
✅ Valid formats:
   • 0912345678    (10 digits starting with 09)
   • +963912345678 (with country code)
   • 963912345678  (country code without +)

❌ Invalid examples:
   • 12345678      (missing prefix)
   • 0812345678    (wrong operator code)
```

---

## 🗓 Registration Flow

```
Student Request → PENDING → Admin Review → APPROVED/REJECTED
                                    ↓
                              Payment Tracking
                                    ↓
                              Student Notified
```

### Payment Statuses
- 🔴 **UNPAID** - No payment received
- 🟡 **PARTIAL** - Partial payment received  
- 🟢 **PAID** - Full payment received

---

## 📅 Google Sheets Format (For Scheduled Posts)

| content | image_url | date | time | platform | status |
|---------|-----------|------|------|----------|--------|
| Post text | https://... | 2024-01-15 | 14:30 | facebook | pending |

- **date**: YYYY-MM-DD (Syria timezone)
- **time**: HH:MM 24-hour format
- **platform**: `facebook`, `instagram`, or `both`
- **status**: `pending` or `published`

---

## 🛠 Tech Stack

| Technology | Usage |
|------------|-------|
| Python 3.10+ | Core language |
| python-telegram-bot | Telegram integration |
| Motor | Async MongoDB driver |
| Google APIs | Drive & Sheets |
| APScheduler | Task scheduling |
| pytz | Timezone handling |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for Training Centers**

</div>
