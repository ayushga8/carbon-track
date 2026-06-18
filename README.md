# 🌿 CarbonTrack — Carbon Footprint Awareness Platform

A full-stack web application built with **Django** that helps users track, understand, and reduce their carbon footprint through personalized insights, eco-challenges, and community engagement.

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Architecture](#-project-architecture)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Running Tests](#-running-tests)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Security](#-security)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)

---

## ✨ Features

### 🧮 Carbon Calculator
- Track emissions across **5 categories**: Transportation, Home Energy, Food & Diet, Shopping, and Waste
- **27 subcategories** with real EPA/DEFRA emission factors
- Automatic CO₂ calculation based on activity and quantity
- Full CRUD on entries with filtering by category and date range

### 📊 Interactive Dashboard
- Real-time carbon statistics (total, monthly, weekly, daily average)
- **Category breakdown** visualization with chart data
- **Trend analysis** — daily, weekly, and monthly emission trends
- **Global comparison** — compare your footprint against India, US, EU, and global averages
- **Personalized reduction tips** based on your highest-emission categories

### 🏆 Eco-Challenges & Gamification
- Join community eco-challenges with difficulty levels (Easy, Medium, Hard)
- Track progress (0–100%) with automatic completion detection
- Atomic participant counting with `F()` expressions (race-condition safe)
- Filter challenges by category and difficulty

### 🥇 Community Leaderboard
- Ranked by completed challenges and total carbon saved
- Cached queries (5-minute TTL) for performance
- Community-wide statistics (total completed, total carbon saved)

### 🔐 Authentication
- **Email/Password** registration with OTP email verification
- **Google Sign-In** via Firebase Authentication (popup flow)
- **GitHub Sign-In** support
- Profile management with avatar upload, bio, and location
- Secure OTP system with hashed storage and rate limiting

### 📡 REST API
- 4 authenticated endpoints with throttling (100 req/hour)
- Session-based authentication via Django REST Framework
- Paginated responses with serialized data

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.1+, Django REST Framework |
| **Frontend** | HTML5, CSS3 (custom design system), Vanilla JavaScript |
| **Database** | SQLite (dev) / PostgreSQL (production) |
| **Auth** | Django Auth + Firebase Admin SDK |
| **Email** | Gmail SMTP with App Passwords |
| **Static Files** | WhiteNoise (compressed + cached) |
| **Deployment** | Vercel (serverless) |
| **Caching** | Django LocMemCache |

---

## 🏗 Project Architecture

```
CarbonTrack follows a clean Django architecture with service layers:

Views (CBVs) → Services → Models → Database
     ↕              ↕
  Templates      Serializers → REST API
```

**Key Design Patterns:**
- **Service Layer**: Business logic in `services.py` (CarbonCalculatorService, StatsService, InsightsService, OTPService)
- **Context Processors**: Firebase config injected globally
- **Signals**: Auto-create UserProfile on User registration
- **Atomic Operations**: `F()` expressions and `transaction.atomic` for race-condition safety

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip
- Firebase project (for Google/GitHub sign-in)
- Gmail account with App Password (for OTP emails)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ayushga8/carbon-track.git
cd carbon-track

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your actual values (see Environment Variables section)

# 5. Set up Firebase credentials
cp firebase-credentials.json.example firebase-credentials.json
# Replace with your actual Firebase service account key

# 6. Run database migrations
python manage.py migrate

# 7. Load emission factor data (optional)
python manage.py loaddata emission_factors

# 8. Create a superuser (optional)
python manage.py createsuperuser

# 9. Start the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to see the app running.

---

## 🔑 Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Gmail SMTP (for OTP verification emails)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_WEB_API_KEY=your-firebase-web-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-firebase-project-id
```

### Getting Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Go to **App passwords** → Generate a password for "Mail"
4. Use the 16-character password as `EMAIL_HOST_PASSWORD`

### Setting Up Firebase
1. Create a project at [Firebase Console](https://console.firebase.google.com/)
2. Enable **Authentication** → Sign-in methods → Google & GitHub
3. Go to **Project Settings** → General → copy Web API Key, Auth Domain, Project ID
4. Go to **Service Accounts** → Generate new private key → save as `firebase-credentials.json`

---

## 🧪 Running Tests

```bash
# Run all 269 tests
python manage.py test

# Run with verbosity
python manage.py test -v 2

# Run specific app tests
python manage.py test accounts
python manage.py test calculator
python manage.py test challenges
python manage.py test dashboard
python manage.py test api
python manage.py test core

# Run specific test class
python manage.py test accounts.tests.TestFirebaseLoginView
```

### Test Coverage Summary

| App | Test Classes | Tests | Areas Covered |
|---|---|---|---|
| **accounts** | 20 | ~120 | OTP security, forms, views, Firebase auth, models |
| **api** | 4 | ~25 | All 4 REST endpoints, auth, throttling |
| **calculator** | 8 | ~35 | Calculator service, forms, models, views |
| **challenges** | 7 | ~35 | Join, progress, leaderboard, models |
| **core** | 5 | ~13 | Home, about, contact, context processor |
| **dashboard** | 7 | ~25 | Stats service, insights, dashboard view |
| **Total** | **51** | **269** | |

---

## 📡 API Documentation

All endpoints require authentication and are rate-limited to **100 requests/hour**.

### `GET /api/stats/`
Returns aggregated carbon statistics for the authenticated user.

```json
{
  "total_carbon": 156.78,
  "monthly_carbon": 42.30,
  "weekly_carbon": 12.50,
  "entry_count": 45,
  "average_daily": 1.41
}
```

### `GET /api/breakdown/?days=30`
Returns emissions breakdown by category.

```json
[
  { "category": "transport", "total": 65.20, "count": 12 },
  { "category": "energy", "total": 45.80, "count": 8 }
]
```

### `GET /api/trends/?period=daily`
Returns time-series trend data. Periods: `daily`, `weekly`, `monthly`.

```json
[
  { "date": "2026-06-15", "total": 5.20 },
  { "date": "2026-06-16", "total": 3.80 }
]
```

### `GET /api/leaderboard/`
Returns top 20 users ranked by completed challenges (cached for 5 minutes).

```json
[
  { "rank": 1, "username": "eco_warrior", "challenges_completed": 12, "carbon_saved": 450.0 }
]
```

---

## 🚀 Deployment

### Deploy to Vercel

1. **Push to GitHub** (already configured)

2. **Import on Vercel:**
   - Go to [vercel.com](https://vercel.com) → New Project → Import `carbon-track`

3. **Set Environment Variables** in Vercel dashboard:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | A strong random secret key |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `.vercel.app` |
   | `EMAIL_HOST_USER` | Your Gmail address |
   | `EMAIL_HOST_PASSWORD` | Your Gmail app password |
   | `FIREBASE_WEB_API_KEY` | Firebase Web API Key |
   | `FIREBASE_AUTH_DOMAIN` | `your-project.firebaseapp.com` |
   | `FIREBASE_PROJECT_ID` | Your Firebase project ID |
   | `FIREBASE_CREDENTIALS_PATH` | `./firebase-credentials.json` |

4. **Deploy!** Vercel auto-detects the `vercel.json` configuration.

> ⚠️ **Note**: Vercel is serverless — SQLite won't persist between requests. For production data persistence, connect a cloud PostgreSQL database (Vercel Postgres, Supabase, or Neon).

---

## 🔒 Security

This project implements comprehensive security measures:

| Feature | Implementation |
|---|---|
| **OTP Hashing** | OTP codes hashed with `make_password` before DB storage |
| **Timing-Attack Resistance** | `check_password()` for constant-time OTP comparison |
| **Cryptographic RNG** | `secrets.randbelow()` for OTP generation |
| **CSRF Protection** | Django CSRF middleware on all forms |
| **XSS Prevention** | Username regex validation, Django auto-escaping |
| **User Enumeration Prevention** | Generic "Invalid credentials" error on login |
| **Open Redirect Blocking** | `url_has_allowed_host_and_scheme()` validation |
| **Rate Limiting** | OTP resend (3/15min), API throttling (100/hour) |
| **Firebase Token Security** | `check_revoked=True`, email-verified-only account linking |
| **Password Validation** | Length, common, numeric, similarity validators |
| **Production Headers** | HSTS, X-Frame-Options DENY, Content-Type nosniff, XSS filter |
| **Session Security** | HttpOnly cookies, SameSite=Lax, Secure flag in production |
| **Atomic Operations** | `F()` expressions and `@transaction.atomic` prevent race conditions |
| **Secret Management** | All secrets from environment variables, crashes if missing in production |

---

## 📁 Project Structure

```
carbon-track/
├── accounts/                   # User authentication & profiles
│   ├── firebase_auth.py        # Firebase Admin SDK integration
│   ├── forms.py                # Registration, Login, OTP, Profile forms
│   ├── models.py               # UserProfile, EmailOTP models
│   ├── otp_service.py          # OTP generation, verification, rate limiting
│   ├── signals.py              # Auto-create profile on User creation
│   ├── views.py                # Auth views + FirebaseLoginView
│   └── tests.py                # ~120 tests
│
├── api/                        # REST API endpoints
│   ├── serializers.py          # DRF serializers
│   ├── views.py                # Stats, Breakdown, Trends, Leaderboard APIs
│   └── tests.py                # ~25 tests
│
├── calculator/                 # Carbon footprint calculator
│   ├── forms.py                # CarbonEntryForm with validation
│   ├── models.py               # EmissionFactor, CarbonEntry models
│   ├── services.py             # CarbonCalculatorService (27 emission factors)
│   ├── views.py                # Calculator, EntryList, EntryDetail, Delete
│   └── tests.py                # ~35 tests
│
├── challenges/                 # Eco-challenges & gamification
│   ├── models.py               # Challenge, UserChallenge models
│   ├── views.py                # List, Detail, Join, Progress, Leaderboard
│   └── tests.py                # ~35 tests
│
├── core/                       # Landing pages & shared utilities
│   ├── context_processors.py   # Firebase config injection
│   ├── forms.py                # ContactForm
│   ├── views.py                # Home, About, Contact views
│   └── tests.py                # ~13 tests
│
├── dashboard/                  # Analytics & insights
│   ├── services.py             # StatsService, InsightsService
│   ├── views.py                # DashboardView with chart data
│   └── tests.py                # ~25 tests
│
├── carbon_platform/            # Django project config
│   ├── settings.py             # Security-hardened settings
│   ├── urls.py                 # Root URL configuration
│   └── wsgi.py                 # WSGI entry point
│
├── static/                     # Static assets
│   ├── css/main.css            # Custom design system (~40KB)
│   └── js/
│       ├── main.js             # Theme toggle, navigation, animations
│       ├── firebase_auth.js    # Firebase popup auth flow
│       ├── calculator.js       # Dynamic subcategory loading
│       └── dashboard.js        # Chart rendering
│
├── templates/                  # Global templates
│   └── base.html               # Base layout with nav, footer, accessibility
│
├── vercel.json                 # Vercel deployment configuration
├── build_files.sh              # Vercel build script
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── firebase-credentials.json.example  # Firebase service account template
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all **269 tests pass** before submitting a PR:
```bash
python manage.py test
```

---

## 📄 License

This project is developed as part of the **Promptars** initiative for carbon footprint awareness.

---

<p align="center">
  Made with 💚 for a greener planet
</p>
