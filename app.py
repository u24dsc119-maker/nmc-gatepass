import os
import io
import uuid
import base64
import qrcode
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId

# For PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_nmc_gatepass')

# MongoDB Atlas - reads from Vercel environment variable
MONGO_URI = os.environ.get(
    'MONGO_URI',
    "mongodb+srv://nmcuser:nmc123@cluster0.6vdunga.mongodb.net/nmc_gatepass?retryWrites=true&w=majority&authSource=admin"
)
DB_NAME = "nmc_gatepass"

# Singleton MongoDB client (avoids reconnecting on every request in serverless)
_mongo_client = None

def get_db():
    global _mongo_client
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=8000,
                connectTimeoutMS=8000,
                tls=True
            )
        return _mongo_client[DB_NAME]
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")
        _mongo_client = None
        return None

def make_qr_b64(url):
    """Generate QR code as base64 string - no filesystem needed."""
    qr = qrcode.QRCode(version=1, box_size=12, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# --- HOME: GATE DISPLAY SCREEN ---

@app.route('/')
def index():
    """Home page: QR code gate display screen."""
    form_url = request.host_url.rstrip('/') + url_for('visitor_form')
    qr_b64 = make_qr_b64(form_url)
    return render_template('gate.html', qr_code=qr_b64, form_url=form_url)

@app.route('/gate')
def gate_display():
    return redirect(url_for('index'))

# --- VISITOR FORM ---

@app.route('/form', methods=['GET', 'POST'])
def visitor_form():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        street = request.form.get('street', '').strip()
        city = request.form.get('city', '').strip()
        pincode = request.form.get('pincode', '').strip()
        from_address = f"{street}, {city} - {pincode}" if (street and city and pincode) else ''
        purpose = request.form.get('purpose', '').strip()
        person_to_meet = request.form.get('person_to_meet', '').strip()

        ctx = dict(name=name, phone=phone, street=street, city=city,
                   pincode=pincode, purpose=purpose, person_to_meet=person_to_meet)

        # --- Validation ---
        if not all([name, phone, street, city, pincode, purpose, person_to_meet]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('form.html', **ctx)

        if not (3 <= len(name) <= 50):
            flash('Name must be between 3 and 50 characters.', 'danger')
            return render_template('form.html', **ctx)

        if not (3 <= len(person_to_meet) <= 50):
            flash('Person name must be between 3 and 50 characters.', 'danger')
            return render_template('form.html', **ctx)

        if not (5 <= len(purpose) <= 200):
            flash('Purpose must be between 5 and 200 characters.', 'danger')
            return render_template('form.html', **ctx)

        if len(phone) != 10 or not phone.isdigit() or phone[0] not in '6789':
            flash('Please enter a valid 10-digit phone number starting with 6, 7, 8, or 9.', 'danger')
            return render_template('form.html', **ctx)

        if len(pincode) != 6 or not pincode.isdigit():
            flash('Please enter a valid 6-digit pincode.', 'danger')
            return render_template('form.html', **ctx)

        # --- Database ---
        try:
            db = get_db()
            if db is None:
                flash('Database connection error. Please try again.', 'danger')
                return render_template('form.html', **ctx)

            result = db.visitors.insert_one({
                'name': name.title(),
                'phone': phone,
                'from_address': from_address.title(),
                'purpose': purpose.capitalize(),
                'person_to_meet': person_to_meet.title(),
                'status': 'Pending',
                'token': None,
                'entry_time': None,
                'exit_time': None,
                'created_at': datetime.now()
            })
            return redirect(url_for('visitor_status', visitor_id=str(result.inserted_id)))
        except Exception as e:
            print(f"DB insert error: {e}")
            flash('An error occurred. Please try again.', 'danger')
            return render_template('form.html', **ctx)

    return render_template('form.html')

# --- VISITOR STATUS PAGE ---

@app.route('/status/<visitor_id>')
def visitor_status(visitor_id):
    try:
        db = get_db()
        if db is None:
            return render_template('error.html', message="Database connection error."), 500
        visitor = db.visitors.find_one({'_id': ObjectId(visitor_id)})
        if visitor:
            visitor['id'] = str(visitor['_id'])
            # Render the same form template but with visitor data to show status
            return render_template('form.html', visitor=visitor)
        return "Visitor not found", 404
    except Exception as e:
        print(f"Status error: {e}")
        return "Invalid request", 400

# --- VERIFY (Gate Security QR Scan) ---

@app.route('/verify/<token>')
def verify(token):
    try:
        db = get_db()
        if db is None:
            return render_template('verify.html', state='invalid')

        visitor = db.visitors.find_one({'token': token, 'status': 'Approved'})
        if not visitor:
            return render_template('verify.html', state='invalid')

        created_at = visitor['created_at']
        expiry_time = created_at.replace(hour=15, minute=30, second=0, microsecond=0)

        if datetime.now() > expiry_time:
            return render_template('verify.html', state='expired', visitor=visitor, expiry_time=expiry_time)

        if visitor.get('entry_time') is None:
            current_time = datetime.now()
            db.visitors.update_one({'_id': visitor['_id']}, {'$set': {'entry_time': current_time}})
            visitor['entry_time'] = current_time
            state = 'entry_allowed'
        elif visitor.get('exit_time') is None:
            current_time = datetime.now()
            db.visitors.update_one({'_id': visitor['_id']}, {'$set': {'exit_time': current_time}})
            visitor['exit_time'] = current_time
            state = 'exit_recorded'
        else:
            state = 'already_used'

        return render_template('verify.html', state=state, visitor=visitor, expiry_time=expiry_time)
    except Exception as e:
        print(f"Verify error: {e}")
        return render_template('verify.html', state='invalid')

# --- ADMIN ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    try:
        db = get_db()
        visitors = []
        metrics = {'total': 0, 'approved': 0, 'rejected': 0}

        if db is not None:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            q = {'created_at': {'$gte': today_start, '$lt': today_end}}
            metrics['total'] = db.visitors.count_documents(q)
            metrics['approved'] = db.visitors.count_documents({**q, 'status': 'Approved'})
            metrics['rejected'] = db.visitors.count_documents({**q, 'status': 'Rejected'})

            visitors = list(db.visitors.find().sort('created_at', -1))
            for v in visitors:
                v['id'] = str(v['_id'])
    except Exception as e:
        print(f"Admin error: {e}")
        flash('Error loading dashboard.', 'danger')

    return render_template('admin.html', visitors=visitors, metrics=metrics)

@app.route('/approve/<visitor_id>')
def approve_visitor(visitor_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    try:
        db = get_db()
        if db is not None:
            visitor = db.visitors.find_one({'_id': ObjectId(visitor_id)})
            if visitor and visitor['status'] == 'Pending':
                token = str(uuid.uuid4())
                verify_url = request.host_url.rstrip('/') + url_for('verify', token=token)
                qr_b64 = make_qr_b64(verify_url)
                expiry_time = visitor['created_at'].replace(hour=15, minute=30, second=0, microsecond=0)
                pdf_bytes = generate_pdf_bytes(visitor, token, qr_b64, expiry_time)

                db.visitors.update_one(
                    {'_id': ObjectId(visitor_id)},
                    {'$set': {
                        'status': 'Approved',
                        'token': token,
                        'pdf_data': pdf_bytes,
                        'qr_b64': qr_b64
                    }}
                )
                flash(f"Visitor {visitor['name']} approved successfully!", "success")
    except Exception as e:
        print(f"Approve error: {e}")
        flash("Error approving visitor.", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/reject/<visitor_id>')
def reject_visitor(visitor_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    try:
        db = get_db()
        if db is not None:
            db.visitors.update_one({'_id': ObjectId(visitor_id)}, {'$set': {'status': 'Rejected'}})
            flash("Visitor rejected.", "warning")
    except Exception as e:
        print(f"Reject error: {e}")
    return redirect(url_for('admin_dashboard'))

@app.route('/download/<token>')
def download_gatepass(token):
    try:
        db = get_db()
        if db is not None:
            visitor = db.visitors.find_one({'token': token, 'status': 'Approved'})
            if visitor and visitor.get('pdf_data'):
                buf = io.BytesIO(visitor['pdf_data'])
                buf.seek(0)
                return send_file(
                    buf,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"NMC_Gatepass_{visitor['name'].replace(' ','_')}.pdf"
                )
    except Exception as e:
        print(f"Download error: {e}")
    flash("PDF not found or not approved yet.", "danger")
    return redirect(url_for('visitor_form'))

# --- PDF GENERATION (in-memory) ---

def generate_pdf_bytes(visitor, token, qr_b64, expiry_time):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2.0, height - 1*inch, "NMC College")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2.0, height - 1.5*inch, "NMC Visitor Gate Pass")
    c.line(1*inch, height - 1.7*inch, width - 1*inch, height - 1.7*inch)

    c.setFont("Helvetica", 13)
    y = height - 2.4*inch
    lh = 0.28*inch

    fields = [
        ("Name", visitor['name'].title()),
        ("From", visitor['from_address'].title()),
        ("Phone", visitor['phone']),
        ("Purpose", visitor['purpose'].capitalize()),
        ("To Meet", visitor['person_to_meet'].title()),
        ("Issued", visitor['created_at'].strftime('%d-%m-%Y %I:%M %p')),
    ]
    for label, value in fields:
        c.drawString(1*inch, y, f"{label:<10}: {value}")
        y -= lh

    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.8, 0, 0)
    c.drawString(1*inch, y, f"Valid Until  : {expiry_time.strftime('%d-%m-%Y')} at 3:30 PM")

    # Embed QR from base64
    qr_img = ImageReader(io.BytesIO(base64.b64decode(qr_b64)))
    c.drawImage(qr_img, width - 3*inch, height - 4.2*inch, width=2.2*inch, height=2.2*inch)

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(1*inch, 0.8*inch, "Valid for one-time entry & exit. Must be shown at the security gate before 3:30 PM.")
    c.save()
    buf.seek(0)
    return buf.read()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
