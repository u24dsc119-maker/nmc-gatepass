# Code Explanation: NMC Visitor Gate Pass System

This document provides a technical walkthrough of the codebase for the NMC Visitor Gate Pass System.

## 1. Backend Architecture (`app.py`)
The backend is built using **Flask**, a lightweight Python web framework. It handles routing, database interactions, and PDF generation.

### Key Components:
- **Database Connection (`get_db`)**: Uses `pymongo` to connect to a MongoDB Atlas cluster. It's implemented as a singleton to reuse the connection across requests.
- **Visitor Registration (`visitor_form`)**: 
    - Handles `GET` (displaying the form) and `POST` (submitting data) requests.
    - Includes rigorous validation for phone numbers (10 digits), pincodes (6 digits), and character lengths for all fields.
    - Automatically capitalizes names and addresses using `.title()` before saving to the database.
- **Admin Dashboard (`admin_dashboard`)**: 
    - Protected by a simple session-based login.
    - Displays today's metrics (Total, Approved, Rejected) using MongoDB aggregation.
- **Approval Logic (`approve_visitor`)**: 
    - Generates a unique `uuid4` token for each approved pass.
    - Calls the PDF generation engine and stores the resulting binary data in MongoDB.
- **PDF Generation (`generate_pdf_bytes`)**: 
    - Uses the `reportlab` library to draw a professional gatepass in memory.
    - Embeds a QR code containing a secure verification URL.

## 2. Frontend Templates (`templates/`)
The frontend uses **Jinja2** templating and **Bootstrap 5** for styling.

### Key Files:
- **`form.html`**: A dual-purpose template.
    - **Registration Mode**: Displays the visitor form with HTML5 validation (`minlength`, `maxlength`, `pattern`).
    - **Status Mode**: If a visitor ID is provided, it hides the form and shows a real-time status card (Pending/Approved/Rejected). It includes a JavaScript `setTimeout` to refresh the page every 10 seconds for live updates.
- **`gate.html`**: The main display for the college gate, showing a static QR code that visitors scan to open the registration form.
- **`admin.html`**: A comprehensive table showing visitor logs, timestamps (entry/exit), and action buttons for approval/rejection.
- **`verify.html`**: The page scanned by security guards. It checks the token validity and records entry/exit times in the database.

## 3. Security Design
- **Unique Tokens**: Every gatepass has a unique random token, making it impossible to guess or forge URLs.
- **Expiry Logic**: Passes are programmed to expire at 3:30 PM on the day of issue.
- **State Management**: The system tracks whether a visitor has already entered or exited, preventing a single pass from being used multiple times.

## 4. Dependencies (`requirements.txt`)
- `Flask`: Web server.
- `pymongo`: Database driver.
- `reportlab`: PDF generation.
- `qrcode`: QR code generation.
- `dnspython`: Required for MongoDB Atlas SRV connections.

---
**Technical Documentation**
**Date:** March 1, 2026
