# TechClub — Professional Networking & Community Platform

> **Tagline:** Connect. Learn. Build Together.  
> **Location:** Hargeisa, Somaliland  
> **Official WhatsApp Contact:** [+252 63 7170860](https://api.whatsapp.com/send?phone=252637170860)  
> **Tech Stack:** Python 3.11, Django 5.2, PostgreSQL 18, Tailwind CSS, Vanilla JavaScript

---

## 🚀 About TechClub

TechClub is a production-grade community management and professional networking platform uniting emerging tech talent, self-taught builders, and senior software engineers across the Horn of Africa. 

The platform bridges the gap between academic theory, tutorials, and commercial software engineering by offering architecture reviews, 1-on-1 mentorship, technical masterclasses, verified digital credentials, and institutional partnerships with leading telecom, banking, and tech enterprises.

---

## ✨ Key System Features

### 1. 🌐 Public Community Portal
* **Homepage (`/`)**: Dynamic hero, vetted member proof counters, core pillars, upcoming event teasers, and institutional endorsements.
* **Meet the Founder (`/founder/`)**: Official founder profile (Ahmed Liban Mohamed), story, vision, and direct verified WhatsApp contact link.
* **Corporate Partners & Trust (`/partners/`)**: Public showcase of verified corporate sponsors, tiered partnership badges (Strategic, Premier, Ecosystem), and chairman/executive quotes.
* **Events & Labs (`/events/`)**: Public schedule of technical meetups, coding labs, and hackathons with real-time seat tracking and role filters.
* **Member Directory (`/directory/`)**: Searchable roster of verified engineers and designers filterable by domain, seniority, and skills with strict privacy protections.
* **Code of Conduct (`/code-of-conduct/`) & About (`/about/`)**: Community standards and organizational roadmap.

### 2. 📝 Membership Admissions Pipeline (`/apply/`)
* **4-Step Application Wizard**: Personal Details, Technical Background & Stack, Portfolio/GitHub Links, and Goals/Referral Tracking.
* **Anti-Bot Defense**: Hidden honeypot security traps silently discard spam submissions.
* **Admissions Queue**: Applications enter review as `PENDING`—no user account is activated until an organizer reviews and approves.

### 3. 🛡️ Organizer Operations Console (`/admin-ops/`)
* **Real-time Telemetry Dashboard**: Metrics on membership growth, application velocity, check-in rates, satisfaction scores, and referral attribution.
* **Applications Review**: 1-click approvals (auto-generates user accounts and sends activation links), waitlisting, and rejections with internal reviewer notes.
* **Corporate Partners Management (`/admin-ops/partners/`)**: Review incoming sponsorship proposals, approve/reject, edit chairman details, and delete partners with CSRF safety.
* **Ticket Scanner & Attendance (`/admin-ops/ticket-scanner/`)**: In-browser QR code scanner and manual lookup for fast physical event check-ins.
* **Verifiable Digital Credentials & PDF Certificates**: Automated certificate issuance with SHA-256 verification hashes, LinkedIn sharing, and dynamic PDF generation.
* **1-Click System Backup**: Instant JSON backup download of all database tables (users, members, events, attendance, and partners) directly from the console.

### 4. 👤 Member Hub (`/member/dashboard/`)
* Personalized dashboard with event RSVPs, registered tickets, and attendance history.
* Digital tickets with live QR codes for event check-in.
* Downloadable PDF certificates for attended masterclasses.
* Profile customization with privacy controls (`PUBLIC` vs `PRIVATE`).

---

## 🛠️ Tech Stack & Architecture

* **Backend:** Python 3.11, Django 5.2.12
* **Database:** PostgreSQL 18 (with connection pooling)
* **Frontend:** Responsive Vanilla CSS & Tailwind CSS tokens, Material Symbols, JetBrains Mono & Manrope typography
* **Security:** 
  * Strict Role-Based Access Control (`ORGANIZER` vs `MEMBER`)
  * CSRF tokens on 100% of state-changing routes
  * Pillow image validation verifying binary headers (blocks disguised scripts)
  * Honeypot bot mitigation on public forms
  * Dynamic XSS escaping and zero raw SQL injection vectors

---

## ⚡ Quick Start & Local Setup

### 1. Prerequisites
* Python 3.11+
* PostgreSQL 15+ (or SQLite for development)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/liban770/TechClub.git
cd techclub

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database & Migrations
```bash
# Run migrations
python manage.py migrate

# Seed sample data (optional demo users, events, and partners)
python seed_data.py
```

### 4. Run Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running Automated Tests

To run the complete automated test suite:
```bash
python manage.py test
```



## 📄 License & Ownership

© 2025 TechClub Hargeisa. All rights reserved.  
Built for the developer, designer, and innovator of Somaliland.
