# NMC College Visitor Gate Pass System

A digital gate pass management system for NMC College built with Python Flask and MongoDB Atlas.

## Features

- 📱 QR Code based visitor registration (scan at gate → fill form on mobile)
- ✅ Admin portal to approve/reject visitor requests
- 📄 PDF gate pass generation with 3:30 PM same-day expiry
- 🔒 Session-based admin authentication
- 📊 Daily visitor analytics dashboard
- 🚪 Entry/Exit tracking via QR scan at security gate

## Tech Stack

- **Backend**: Python Flask
- **Database**: MongoDB Atlas
- **PDF**: ReportLab
- **QR Code**: qrcode (pillow)
- **Frontend**: Bootstrap 5

## URLs

| URL | Purpose |
|-----|---------|
| `/` | Gate display — QR code screen |
| `/form` | Visitor registration form |
| `/status/<id>` | Visitor approval status & PDF download |
| `/login` | Admin portal login |
| `/admin` | Admin dashboard |
| `/verify/<token>` | Security gate scan |

## Setup

```bash
pip install -r requirements.txt
python app.py
```

## Admin Credentials

- Username: `admin`
- Password: `admin123`
