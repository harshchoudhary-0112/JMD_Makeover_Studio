import os
import sqlite3
from functools import wraps
from datetime import date, datetime

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, g, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jmd_studio.db')


# ─── Database Helper ───────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ─── File Upload Helper ───────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


# ─── Email Helper ──────────────────────────────────────────────
def send_email(to_email, subject, body):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        sender = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')
        if not sender or not password or sender == 'your-email@gmail.com':
            print(f"[EMAIL SKIPPED] To: {to_email}, Subject: {subject}")
            return

        msg = MIMEMultipart()
        msg['From'] = f"JMD Makeover Studio <{sender}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        print(f"[EMAIL SENT] To: {to_email}, Subject: {subject}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


# ─── SMS Helper ────────────────────────────────────────────────
def send_sms(phone, message):
    try:
        from twilio.rest import Client
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
        if not sid or not token or sid == 'your-twilio-sid':
            print(f"[SMS SKIPPED] To: {phone}, Message: {message}")
            return
        client = Client(sid, token)
        phone = '+91' + phone[-10:]
        client.messages.create(body=message, from_=twilio_number, to=phone)
        print(f"[SMS SENT] To: {phone}")
    except Exception as e:
        print(f"[SMS ERROR] {e}")


# ─── Notification Helper ──────────────────────────────────────
def add_notification(user_id, title, message, notif_type='info'):
    db = get_db()
    db.execute('INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, ?)',
               (user_id, title, message, notif_type))
    db.commit()


# ─── Auth Decorators ──────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin login required.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ─── Context Processor ────────────────────────────────────────
def get_settings():
    """Load all site settings as a dict."""
    db = get_db()
    rows = db.execute('SELECT key, value FROM site_settings').fetchall()
    return {row['key']: row['value'] for row in rows}


@app.context_processor
def inject_user():
    user = None
    unread_count = 0
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        unread_count = db.execute('SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0',
                                  (session['user_id'],)).fetchone()[0]
    settings = get_settings()
    return dict(current_user=user, unread_count=unread_count, site=settings)


# ═══════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def home():
    db = get_db()
    services = db.execute('SELECT * FROM services WHERE is_active = 1 LIMIT 6').fetchall()
    courses = db.execute('SELECT * FROM courses WHERE is_active = 1 LIMIT 4').fetchall()
    today = date.today().isoformat()
    offers = db.execute('SELECT * FROM offers WHERE is_active = 1 AND end_date >= ? LIMIT 3', (today,)).fetchall()
    upcoming_events = db.execute('SELECT * FROM events WHERE is_active = 1 AND event_date >= ? ORDER BY event_date ASC LIMIT 3', (today,)).fetchall()
    return render_template('home.html', services=services, courses=courses, offers=offers, events=upcoming_events)


@app.route('/services')
def services():
    db = get_db()
    all_services = db.execute('SELECT * FROM services WHERE is_active = 1').fetchall()
    return render_template('services.html', services=all_services)


@app.route('/academy')
def academy():
    db = get_db()
    courses = db.execute('SELECT * FROM courses WHERE is_active = 1').fetchall()
    return render_template('academy.html', courses=courses)


@app.route('/offers')
def offers():
    db = get_db()
    today = date.today().isoformat()
    active_offers = db.execute('SELECT * FROM offers WHERE is_active = 1 AND end_date >= ?', (today,)).fetchall()
    return render_template('offers.html', offers=active_offers)


@app.route('/offer/<int:id>')
def offer_detail(id):
    db = get_db()
    offer = db.execute('SELECT * FROM offers WHERE id = ? AND is_active = 1', (id,)).fetchone()
    if not offer:
        flash('Offer not found.', 'error')
        return redirect(url_for('offers'))
    registrations = db.execute('SELECT COUNT(*) FROM offer_registrations WHERE offer_id = ?', (id,)).fetchone()[0]
    return render_template('offer_detail.html', offer=offer, registrations=registrations)


@app.route('/course/<int:id>')
def course_detail(id):
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ? AND is_active = 1', (id,)).fetchone()
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('academy'))
    registrations = db.execute('SELECT COUNT(*) FROM course_registrations WHERE course_id = ?', (id,)).fetchone()[0]
    return render_template('course_detail.html', course=course, registrations=registrations)


@app.route('/events')
def events():
    db = get_db()
    all_events = db.execute('SELECT * FROM events WHERE is_active = 1 ORDER BY event_date ASC').fetchall()
    return render_template('events.html', events=all_events)


@app.route('/event/<int:id>')
def event_detail(id):
    db = get_db()
    event = db.execute('SELECT * FROM events WHERE id = ? AND is_active = 1', (id,)).fetchone()
    if not event:
        flash('Event not found.', 'error')
        return redirect(url_for('events'))
    registrations = db.execute('SELECT COUNT(*) FROM event_registrations WHERE event_id = ?', (id,)).fetchone()[0]
    return render_template('event_detail.html', event=event, registrations=registrations)


@app.route('/register-event/<int:id>', methods=['POST'])
@login_required
def register_event(id):
    db = get_db()
    user_id = session['user_id']
    existing = db.execute('SELECT id FROM event_registrations WHERE event_id = ? AND user_id = ?',
                          (id, user_id)).fetchone()
    if existing:
        flash('You are already registered for this event.', 'info')
    else:
        db.execute('INSERT INTO event_registrations (event_id, user_id) VALUES (?, ?)', (id, user_id))
        event = db.execute('SELECT title FROM events WHERE id = ?', (id,)).fetchone()
        db.execute('INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, ?)',
                   (user_id, 'Event Registration',
                    f"You've registered for {event['title']}. We'll send you updates!", 'success'))
        db.commit()
        flash(f"Successfully registered for {event['title']}!", 'success')
    return redirect(url_for('event_detail', id=id))


@app.route('/gallery')
def gallery():
    db = get_db()
    images = db.execute('SELECT * FROM gallery ORDER BY created_at DESC').fetchall()
    return render_template('gallery.html', images=images)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not message:
            flash('Name and message are required.', 'error')
            return redirect(url_for('contact'))

        db = get_db()
        db.execute('INSERT INTO contact_inquiries (name, email, phone, subject, message) VALUES (?, ?, ?, ?, ?)',
                   (name, email, phone, subject, message))
        db.commit()

        # Notify admin
        admin_email = os.getenv('ADMIN_NOTIFY_EMAIL')
        if admin_email:
            send_email(admin_email, f'New Inquiry from {name}',
                       f'Name: {name}\nEmail: {email}\nPhone: {phone}\nSubject: {subject}\nMessage: {message}')

        flash('Your inquiry has been submitted. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


# ═══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        # Validations
        if not all([name, email, phone, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('signup'))
        if len(phone) < 10:
            flash('Please enter a valid phone number.', 'error')
            return redirect(url_for('signup'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('signup'))
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('signup'))

        hashed = generate_password_hash(password)
        db.execute('INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)',
                   (name, email, phone, hashed))
        db.commit()

        # Get user id
        user = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

        # Welcome notification
        add_notification(user['id'], 'Welcome!', f'Welcome to JMD Makeover Studio, {name}!', 'success')
        send_email(email, 'Welcome to JMD Makeover Studio',
                   f'Hi {name},\n\nWelcome to JMD Makeover Studio & Academy! Your account has been created successfully.\n\nLogin: {email}\n\nThank you!')
        send_sms(phone, f'Welcome to JMD Makeover Studio, {name}! Your account is ready.')

        # Auto login
        session['user_id'] = user['id']
        session['user_name'] = name
        flash(f'Welcome, {name}! Your account has been created.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('login'))

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# ═══════════════════════════════════════════════════════════════
#  USER ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/user-dashboard')
@login_required
def user_dashboard():
    db = get_db()
    uid = session['user_id']
    appointments = db.execute(
        'SELECT a.*, s.name as service_name FROM appointments a LEFT JOIN services s ON a.service_id = s.id WHERE a.user_id = ? ORDER BY a.created_at DESC LIMIT 5', (uid,)).fetchall()
    course_regs = db.execute(
        'SELECT cr.*, c.title as course_title FROM course_registrations cr LEFT JOIN courses c ON cr.course_id = c.id WHERE cr.user_id = ? ORDER BY cr.created_at DESC LIMIT 5', (uid,)).fetchall()
    offer_regs = db.execute(
        'SELECT oreg.*, o.title as offer_title FROM offer_registrations oreg LEFT JOIN offers o ON oreg.offer_id = o.id WHERE oreg.user_id = ? ORDER BY oreg.created_at DESC LIMIT 5', (uid,)).fetchall()
    notifications = db.execute(
        'SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', (uid,)).fetchall()

    # Mark notifications as read
    db.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (uid,))
    db.commit()

    stats = {
        'total_appointments': db.execute('SELECT COUNT(*) FROM appointments WHERE user_id = ?', (uid,)).fetchone()[0],
        'pending': db.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ? AND status = 'Pending'", (uid,)).fetchone()[0],
        'approved': db.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ? AND status = 'Approved'", (uid,)).fetchone()[0],
        'completed': db.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ? AND status = 'Completed'", (uid,)).fetchone()[0],
    }

    return render_template('user_dashboard.html', appointments=appointments,
                           course_regs=course_regs, offer_regs=offer_regs,
                           notifications=notifications, stats=stats)


@app.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    db = get_db()
    if request.method == 'POST':
        service_id = request.form.get('service_id')
        appt_date = request.form.get('appointment_date', '').strip()
        appt_time = request.form.get('appointment_time', '').strip()
        message = request.form.get('message', '').strip()

        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        # Validate date
        if not appt_date or not appt_time:
            flash('Date and time are required.', 'error')
            return redirect(url_for('book_appointment'))

        if appt_date < date.today().isoformat():
            flash('Cannot book appointment for a past date.', 'error')
            return redirect(url_for('book_appointment'))

        service = db.execute('SELECT * FROM services WHERE id = ?', (service_id,)).fetchone()
        service_name = service['name'] if service else 'General'

        db.execute('''INSERT INTO appointments (user_id, service_id, name, email, phone,
                      appointment_date, appointment_time, message) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (session['user_id'], service_id, user['name'], user['email'],
                    user['phone'], appt_date, appt_time, message))
        db.commit()

        # Notifications
        add_notification(session['user_id'], 'Appointment Booked',
                         f'Your appointment for {service_name} on {appt_date} at {appt_time} has been submitted. Awaiting admin approval.',
                         'info')

        send_email(user['email'], 'Appointment Booking Request - JMD Makeover Studio',
                   f"Hi {user['name']},\n\nYour appointment request has been received.\n\nService: {service_name}\nDate: {appt_date}\nTime: {appt_time}\n\nWe will confirm your appointment shortly.\n\nThank you!\nJMD Makeover Studio")

        send_sms(user['phone'], f"JMD Studio: Your booking for {service_name} on {appt_date} at {appt_time} is received. Awaiting confirmation.")

        # Notify admin
        admin_email = os.getenv('ADMIN_NOTIFY_EMAIL')
        admin_phone = os.getenv('ADMIN_NOTIFY_PHONE')
        if admin_email:
            send_email(admin_email, 'New Appointment Request',
                       f"New appointment from {user['name']}.\nService: {service_name}\nDate: {appt_date}\nTime: {appt_time}\nPhone: {user['phone']}")
        if admin_phone:
            send_sms(admin_phone, f"New appointment: {user['name']} for {service_name} on {appt_date} at {appt_time}")

        flash('Appointment booked successfully! Awaiting admin approval.', 'success')
        return redirect(url_for('my_appointments'))

    services = db.execute('SELECT * FROM services WHERE is_active = 1').fetchall()
    return render_template('book_appointment.html', services=services, today=date.today().isoformat())


@app.route('/my-appointments')
@login_required
def my_appointments():
    db = get_db()
    appointments = db.execute(
        'SELECT a.*, s.name as service_name FROM appointments a LEFT JOIN services s ON a.service_id = s.id WHERE a.user_id = ? ORDER BY a.created_at DESC',
        (session['user_id'],)).fetchall()
    return render_template('my_appointments.html', appointments=appointments)


@app.route('/cancel-appointment/<int:id>', methods=['POST'])
@login_required
def cancel_appointment(id):
    db = get_db()
    appt = db.execute('SELECT * FROM appointments WHERE id = ? AND user_id = ?',
                      (id, session['user_id'])).fetchone()
    if appt and appt['status'] in ('Pending', 'Approved'):
        db.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (id,))
        db.commit()
        add_notification(session['user_id'], 'Appointment Cancelled',
                         'Your appointment has been cancelled.', 'warning')
        flash('Appointment cancelled.', 'info')
    else:
        flash('Cannot cancel this appointment.', 'error')
    return redirect(url_for('my_appointments'))


@app.route('/register-course/<int:id>', methods=['GET', 'POST'])
@login_required
def register_course(id):
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ? AND is_active = 1', (id,)).fetchone()
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('academy'))

    if request.method == 'POST':
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        # Check duplicate
        existing = db.execute('SELECT id FROM course_registrations WHERE user_id = ? AND course_id = ?',
                              (session['user_id'], id)).fetchone()
        if existing:
            flash('You have already registered for this course.', 'warning')
            return redirect(url_for('academy'))

        db.execute('''INSERT INTO course_registrations (user_id, course_id, name, email, phone)
                      VALUES (?, ?, ?, ?, ?)''',
                   (session['user_id'], id, user['name'], user['email'], user['phone']))
        db.commit()

        add_notification(session['user_id'], 'Course Registration',
                         f"You registered for {course['title']}. Awaiting confirmation.", 'info')

        send_email(user['email'], f"Course Registration - {course['title']}",
                   f"Hi {user['name']},\n\nYou have registered for {course['title']}.\nDuration: {course['duration']}\nFees: ₹{course['fees']}\n\nWe will contact you shortly.\n\nJMD Makeover Studio & Academy")

        send_sms(user['phone'], f"JMD Academy: Registration for {course['title']} received. We'll contact you soon.")

        # Notify admin
        admin_email = os.getenv('ADMIN_NOTIFY_EMAIL')
        if admin_email:
            send_email(admin_email, f"New Course Registration - {course['title']}",
                       f"Student: {user['name']}\nEmail: {user['email']}\nPhone: {user['phone']}\nCourse: {course['title']}")

        flash(f"Registered for {course['title']} successfully!", 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('book_appointment.html', course=course)


@app.route('/register-offer/<int:id>', methods=['POST'])
@login_required
def register_offer(id):
    db = get_db()
    offer = db.execute('SELECT * FROM offers WHERE id = ? AND is_active = 1', (id,)).fetchone()
    if not offer:
        flash('Offer not found.', 'error')
        return redirect(url_for('offers'))

    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    # Check duplicate
    existing = db.execute('SELECT id FROM offer_registrations WHERE user_id = ? AND offer_id = ?',
                          (session['user_id'], id)).fetchone()
    if existing:
        flash('You have already registered for this offer.', 'warning')
        return redirect(url_for('offers'))

    db.execute('''INSERT INTO offer_registrations (user_id, offer_id, name, email, phone)
                  VALUES (?, ?, ?, ?, ?)''',
               (session['user_id'], id, user['name'], user['email'], user['phone']))
    db.commit()

    add_notification(session['user_id'], 'Offer Registration',
                     f"You registered for {offer['title']}.", 'info')

    send_email(user['email'], f"Offer Registration - {offer['title']}",
               f"Hi {user['name']},\n\nYou registered for: {offer['title']}\nDiscount: {offer['discount']}\n\nWe will contact you shortly.\n\nJMD Makeover Studio")

    send_sms(user['phone'], f"JMD Studio: You registered for {offer['title']}. We'll contact you soon.")

    admin_email = os.getenv('ADMIN_NOTIFY_EMAIL')
    if admin_email:
        send_email(admin_email, f"New Offer Registration - {offer['title']}",
                   f"User: {user['name']}\nEmail: {user['email']}\nPhone: {user['phone']}\nOffer: {offer['title']}")

    flash(f"Registered for {offer['title']} successfully!", 'success')
    return redirect(url_for('offers'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()

        if not name or not phone:
            flash('Name and phone are required.', 'error')
            return redirect(url_for('profile'))

        db.execute('UPDATE users SET name = ?, phone = ? WHERE id = ?',
                   (name, phone, session['user_id']))

        if new_password:
            if not current_password or not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('profile'))
            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'error')
                return redirect(url_for('profile'))
            hashed = generate_password_hash(new_password)
            db.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, session['user_id']))

        db.commit()
        session['user_name'] = name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


# ═══════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        db = get_db()
        admin = db.execute('SELECT * FROM admins WHERE email = ?', (email,)).fetchone()

        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            session['admin_email'] = admin['email']
            flash('Welcome, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        'total_users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'total_appointments': db.execute('SELECT COUNT(*) FROM appointments').fetchone()[0],
        'pending_appointments': db.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Pending'").fetchone()[0],
        'approved_appointments': db.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Approved'").fetchone()[0],
        'completed_appointments': db.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed'").fetchone()[0],
        'total_services': db.execute('SELECT COUNT(*) FROM services').fetchone()[0],
        'total_courses': db.execute('SELECT COUNT(*) FROM courses').fetchone()[0],
        'total_offers': db.execute('SELECT COUNT(*) FROM offers WHERE is_active = 1').fetchone()[0],
        'course_registrations': db.execute('SELECT COUNT(*) FROM course_registrations').fetchone()[0],
        'offer_registrations': db.execute('SELECT COUNT(*) FROM offer_registrations').fetchone()[0],
        'gallery_images': db.execute('SELECT COUNT(*) FROM gallery').fetchone()[0],
        'total_events': db.execute('SELECT COUNT(*) FROM events WHERE is_active = 1').fetchone()[0],
        'event_registrations': db.execute('SELECT COUNT(*) FROM event_registrations').fetchone()[0],
    }
    recent_appointments = db.execute(
        'SELECT a.*, s.name as service_name FROM appointments a LEFT JOIN services s ON a.service_id = s.id ORDER BY a.created_at DESC LIMIT 5').fetchall()
    return render_template('admin_dashboard.html', stats=stats, recent_appointments=recent_appointments)


@app.route('/manage-appointments')
@admin_required
def manage_appointments():
    db = get_db()
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        appointments = db.execute(
            'SELECT a.*, s.name as service_name FROM appointments a LEFT JOIN services s ON a.service_id = s.id WHERE a.status = ? ORDER BY a.created_at DESC',
            (status_filter,)).fetchall()
    else:
        appointments = db.execute(
            'SELECT a.*, s.name as service_name FROM appointments a LEFT JOIN services s ON a.service_id = s.id ORDER BY a.created_at DESC').fetchall()
    return render_template('manage_appointments.html', appointments=appointments, status_filter=status_filter)


@app.route('/approve-appointment/<int:id>', methods=['POST'])
@admin_required
def approve_appointment(id):
    db = get_db()
    appt = db.execute('SELECT * FROM appointments WHERE id = ?', (id,)).fetchone()
    if appt:
        admin_note = request.form.get('admin_note', '').strip()
        db.execute("UPDATE appointments SET status = 'Approved', admin_note = ? WHERE id = ?", (admin_note, id))
        db.commit()

        service = db.execute('SELECT name FROM services WHERE id = ?', (appt['service_id'],)).fetchone()
        service_name = service['name'] if service else 'Service'

        if appt['user_id']:
            add_notification(appt['user_id'], 'Appointment Approved',
                             f"Your appointment for {service_name} on {appt['appointment_date']} at {appt['appointment_time']} has been approved!", 'success')

        send_email(appt['email'], 'Appointment Approved - JMD Makeover Studio',
                   f"Hi {appt['name']},\n\nYour appointment has been approved!\n\nService: {service_name}\nDate: {appt['appointment_date']}\nTime: {appt['appointment_time']}\n{f'Note: {admin_note}' if admin_note else ''}\n\nSee you soon!\nJMD Makeover Studio")

        send_sms(appt['phone'], f"JMD Studio: Your appointment for {service_name} on {appt['appointment_date']} at {appt['appointment_time']} is APPROVED!")

        flash('Appointment approved and user notified.', 'success')
    return redirect(url_for('manage_appointments'))


@app.route('/reject-appointment/<int:id>', methods=['POST'])
@admin_required
def reject_appointment(id):
    db = get_db()
    appt = db.execute('SELECT * FROM appointments WHERE id = ?', (id,)).fetchone()
    if appt:
        admin_note = request.form.get('admin_note', '').strip()
        db.execute("UPDATE appointments SET status = 'Rejected', admin_note = ? WHERE id = ?", (admin_note, id))
        db.commit()

        if appt['user_id']:
            add_notification(appt['user_id'], 'Appointment Rejected',
                             f"Your appointment on {appt['appointment_date']} has been rejected. {admin_note}", 'error')

        send_email(appt['email'], 'Appointment Update - JMD Makeover Studio',
                   f"Hi {appt['name']},\n\nWe regret to inform you that your appointment on {appt['appointment_date']} could not be accommodated.\n\n{f'Reason: {admin_note}' if admin_note else ''}\n\nPlease try booking for a different date.\n\nJMD Makeover Studio")

        send_sms(appt['phone'], f"JMD Studio: Your appointment on {appt['appointment_date']} was not approved. Please try another date.")

        flash('Appointment rejected and user notified.', 'info')
    return redirect(url_for('manage_appointments'))


@app.route('/reschedule-appointment/<int:id>', methods=['POST'])
@admin_required
def reschedule_appointment(id):
    db = get_db()
    appt = db.execute('SELECT * FROM appointments WHERE id = ?', (id,)).fetchone()
    if appt:
        new_date = request.form.get('new_date', '').strip()
        new_time = request.form.get('new_time', '').strip()
        admin_note = request.form.get('admin_note', '').strip()

        if not new_date or not new_time:
            flash('New date and time are required for rescheduling.', 'error')
            return redirect(url_for('manage_appointments'))

        db.execute("UPDATE appointments SET appointment_date = ?, appointment_time = ?, status = 'Rescheduled', admin_note = ? WHERE id = ?",
                   (new_date, new_time, admin_note, id))
        db.commit()

        if appt['user_id']:
            add_notification(appt['user_id'], 'Appointment Rescheduled',
                             f"Your appointment has been rescheduled to {new_date} at {new_time}.", 'warning')

        send_email(appt['email'], 'Appointment Rescheduled - JMD Makeover Studio',
                   f"Hi {appt['name']},\n\nYour appointment has been rescheduled.\n\nNew Date: {new_date}\nNew Time: {new_time}\n{f'Note: {admin_note}' if admin_note else ''}\n\nJMD Makeover Studio")

        send_sms(appt['phone'], f"JMD Studio: Your appointment is rescheduled to {new_date} at {new_time}.")

        flash('Appointment rescheduled and user notified.', 'success')
    return redirect(url_for('manage_appointments'))


@app.route('/complete-appointment/<int:id>', methods=['POST'])
@admin_required
def complete_appointment(id):
    db = get_db()
    appt = db.execute('SELECT * FROM appointments WHERE id = ?', (id,)).fetchone()
    if appt:
        db.execute("UPDATE appointments SET status = 'Completed' WHERE id = ?", (id,))
        db.commit()

        if appt['user_id']:
            add_notification(appt['user_id'], 'Appointment Completed',
                             'Thank you for visiting JMD Makeover Studio! We hope you loved your experience.', 'success')

        send_email(appt['email'], 'Thank You - JMD Makeover Studio',
                   f"Hi {appt['name']},\n\nThank you for visiting JMD Makeover Studio! We hope you loved your experience.\n\nWe would love to hear your feedback. Visit us again soon!\n\nJMD Makeover Studio")

        send_sms(appt['phone'], f"JMD Studio: Thank you for visiting, {appt['name']}! Hope you loved the experience.")

        flash('Appointment marked as completed.', 'success')
    return redirect(url_for('manage_appointments'))


@app.route('/schedule-appointment', methods=['GET', 'POST'])
@admin_required
def schedule_appointment():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service_id = request.form.get('service_id')
        appt_date = request.form.get('appointment_date', '').strip()
        appt_time = request.form.get('appointment_time', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not phone or not appt_date or not appt_time:
            flash('Name, phone, date, and time are required.', 'error')
            return redirect(url_for('schedule_appointment'))

        db.execute('''INSERT INTO appointments (user_id, service_id, name, email, phone,
                      appointment_date, appointment_time, message, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Approved')''',
                   (None, service_id, name, email, phone, appt_date, appt_time, message))
        db.commit()

        if email:
            service = db.execute('SELECT name FROM services WHERE id = ?', (service_id,)).fetchone()
            service_name = service['name'] if service else 'Service'
            send_email(email, 'Appointment Scheduled - JMD Makeover Studio',
                       f"Hi {name},\n\nYour appointment has been scheduled.\n\nService: {service_name}\nDate: {appt_date}\nTime: {appt_time}\n\nSee you soon!\nJMD Makeover Studio")

        if phone:
            send_sms(phone, f"JMD Studio: Your appointment on {appt_date} at {appt_time} is confirmed.")

        flash('Appointment scheduled successfully!', 'success')
        return redirect(url_for('manage_appointments'))

    services = db.execute('SELECT * FROM services WHERE is_active = 1').fetchall()
    return render_template('schedule_appointment.html', services=services, today=date.today().isoformat())


@app.route('/manage-services', methods=['GET', 'POST'])
@admin_required
def manage_services():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', 0)
            duration = request.form.get('duration', '').strip()
            image = None
            if 'image' in request.files:
                image = save_upload(request.files['image'])

            db.execute('INSERT INTO services (name, description, price, duration, image) VALUES (?, ?, ?, ?, ?)',
                       (name, description, float(price), duration, image))
            db.commit()
            flash('Service added successfully!', 'success')

        elif action == 'update':
            sid = request.form.get('service_id')
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', 0)
            duration = request.form.get('duration', '').strip()

            if 'image' in request.files and request.files['image'].filename:
                image = save_upload(request.files['image'])
                db.execute('UPDATE services SET name=?, description=?, price=?, duration=?, image=? WHERE id=?',
                           (name, description, float(price), duration, image, sid))
            else:
                db.execute('UPDATE services SET name=?, description=?, price=?, duration=? WHERE id=?',
                           (name, description, float(price), duration, sid))
            db.commit()
            flash('Service updated successfully!', 'success')

        elif action == 'delete':
            sid = request.form.get('service_id')
            db.execute('DELETE FROM services WHERE id = ?', (sid,))
            db.commit()
            flash('Service deleted.', 'info')

        elif action == 'toggle':
            sid = request.form.get('service_id')
            service = db.execute('SELECT is_active FROM services WHERE id = ?', (sid,)).fetchone()
            new_status = 0 if service['is_active'] else 1
            db.execute('UPDATE services SET is_active = ? WHERE id = ?', (new_status, sid))
            db.commit()
            flash('Service status updated.', 'info')

        return redirect(url_for('manage_services'))

    services = db.execute('SELECT * FROM services ORDER BY id DESC').fetchall()
    return render_template('manage_services.html', services=services)


@app.route('/manage-courses', methods=['GET', 'POST'])
@admin_required
def manage_courses():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            duration = request.form.get('duration', '').strip()
            fees = request.form.get('fees', 0)
            image = None
            if 'image' in request.files:
                image = save_upload(request.files['image'])

            db.execute('INSERT INTO courses (title, description, duration, fees, image) VALUES (?, ?, ?, ?, ?)',
                       (title, description, duration, float(fees), image))
            db.commit()
            flash('Course added successfully!', 'success')

        elif action == 'update':
            cid = request.form.get('course_id')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            duration = request.form.get('duration', '').strip()
            fees = request.form.get('fees', 0)

            if 'image' in request.files and request.files['image'].filename:
                image = save_upload(request.files['image'])
                db.execute('UPDATE courses SET title=?, description=?, duration=?, fees=?, image=? WHERE id=?',
                           (title, description, duration, float(fees), image, cid))
            else:
                db.execute('UPDATE courses SET title=?, description=?, duration=?, fees=? WHERE id=?',
                           (title, description, duration, float(fees), cid))
            db.commit()
            flash('Course updated successfully!', 'success')

        elif action == 'delete':
            cid = request.form.get('course_id')
            db.execute('DELETE FROM courses WHERE id = ?', (cid,))
            db.commit()
            flash('Course deleted.', 'info')

        elif action == 'toggle':
            cid = request.form.get('course_id')
            course = db.execute('SELECT is_active FROM courses WHERE id = ?', (cid,)).fetchone()
            new_status = 0 if course['is_active'] else 1
            db.execute('UPDATE courses SET is_active = ? WHERE id = ?', (new_status, cid))
            db.commit()
            flash('Course status updated.', 'info')

        return redirect(url_for('manage_courses'))

    courses = db.execute('SELECT * FROM courses ORDER BY id DESC').fetchall()
    return render_template('manage_courses.html', courses=courses)


@app.route('/manage-offers', methods=['GET', 'POST'])
@admin_required
def manage_offers():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            discount = request.form.get('discount', '').strip()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()
            image = None
            if 'image' in request.files:
                image = save_upload(request.files['image'])

            db.execute('INSERT INTO offers (title, description, discount, start_date, end_date, image) VALUES (?, ?, ?, ?, ?, ?)',
                       (title, description, discount, start_date, end_date, image))
            db.commit()

            # Notify all users about new offer
            users = db.execute('SELECT * FROM users').fetchall()
            for user in users:
                add_notification(user['id'], 'New Offer!', f"{title} - {discount}! Valid till {end_date}.", 'info')
                send_email(user['email'], f'New Offer - {title} | JMD Makeover Studio',
                           f"Hi {user['name']},\n\nExciting news! {title}\n\n{description}\nDiscount: {discount}\nValid: {start_date} to {end_date}\n\nBook now!\nJMD Makeover Studio")

            flash('Offer added and users notified!', 'success')

        elif action == 'update':
            oid = request.form.get('offer_id')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            discount = request.form.get('discount', '').strip()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()

            if 'image' in request.files and request.files['image'].filename:
                image = save_upload(request.files['image'])
                db.execute('UPDATE offers SET title=?, description=?, discount=?, start_date=?, end_date=?, image=? WHERE id=?',
                           (title, description, discount, start_date, end_date, image, oid))
            else:
                db.execute('UPDATE offers SET title=?, description=?, discount=?, start_date=?, end_date=? WHERE id=?',
                           (title, description, discount, start_date, end_date, oid))
            db.commit()
            flash('Offer updated successfully!', 'success')

        elif action == 'delete':
            oid = request.form.get('offer_id')
            db.execute('DELETE FROM offers WHERE id = ?', (oid,))
            db.commit()
            flash('Offer deleted.', 'info')

        elif action == 'toggle':
            oid = request.form.get('offer_id')
            offer = db.execute('SELECT is_active FROM offers WHERE id = ?', (oid,)).fetchone()
            new_status = 0 if offer['is_active'] else 1
            db.execute('UPDATE offers SET is_active = ? WHERE id = ?', (new_status, oid))
            db.commit()
            flash('Offer status updated.', 'info')

        return redirect(url_for('manage_offers'))

    all_offers = db.execute('SELECT * FROM offers ORDER BY id DESC').fetchall()
    return render_template('manage_offers.html', offers=all_offers)


@app.route('/course-registrations')
@admin_required
def course_registrations():
    db = get_db()
    c_regs = db.execute(
        'SELECT cr.*, c.title as course_title FROM course_registrations cr LEFT JOIN courses c ON cr.course_id = c.id ORDER BY cr.created_at DESC').fetchall()
    o_regs = db.execute(
        'SELECT oreg.*, o.title as offer_title FROM offer_registrations oreg LEFT JOIN offers o ON oreg.offer_id = o.id ORDER BY oreg.created_at DESC').fetchall()
    return render_template('course_registrations.html', course_regs=c_regs, offer_regs=o_regs)


@app.route('/manage-gallery', methods=['GET', 'POST'])
@admin_required
def manage_gallery():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'upload':
            caption = request.form.get('caption', '').strip()
            if 'image' in request.files:
                image = save_upload(request.files['image'])
                if image:
                    db.execute('INSERT INTO gallery (image, caption) VALUES (?, ?)', (image, caption))
                    db.commit()
                    flash('Image uploaded successfully!', 'success')
                else:
                    flash('Invalid file type. Allowed: jpg, jpeg, png, webp.', 'error')
            else:
                flash('Please select an image.', 'error')

        elif action == 'delete':
            gid = request.form.get('gallery_id')
            img = db.execute('SELECT image FROM gallery WHERE id = ?', (gid,)).fetchone()
            if img:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], img['image'])
                if os.path.exists(filepath):
                    os.remove(filepath)
            db.execute('DELETE FROM gallery WHERE id = ?', (gid,))
            db.commit()
            flash('Image deleted.', 'info')

        return redirect(url_for('manage_gallery'))

    images = db.execute('SELECT * FROM gallery ORDER BY created_at DESC').fetchall()
    return render_template('manage_gallery.html', images=images)


@app.route('/manage-users')
@admin_required
def manage_users():
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    return render_template('manage_users.html', users=users)


@app.route('/manage-events', methods=['GET', 'POST'])
@admin_required
def manage_events():
    db = get_db()

    if request.method == 'POST':
        action = request.form.get('action')
        event_id = request.form.get('event_id')

        if action == 'add':
            title = request.form.get('title')
            description = request.form.get('description', '')
            event_date = request.form.get('event_date', '')
            event_time = request.form.get('event_time', '')
            venue = request.form.get('venue', '')
            fees = float(request.form.get('fees', 0) or 0)
            image = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    image = save_upload(file)
            db.execute('INSERT INTO events (title, description, event_date, event_time, venue, fees, image) VALUES (?,?,?,?,?,?,?)',
                       (title, description, event_date, event_time, venue, fees, image))
            db.commit()
            flash('Event added!', 'success')

        elif action == 'update':
            title = request.form.get('title')
            description = request.form.get('description', '')
            event_date = request.form.get('event_date', '')
            event_time = request.form.get('event_time', '')
            venue = request.form.get('venue', '')
            fees = float(request.form.get('fees', 0) or 0)
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    image = save_upload(file)
                    db.execute('UPDATE events SET title=?, description=?, event_date=?, event_time=?, venue=?, fees=?, image=? WHERE id=?',
                               (title, description, event_date, event_time, venue, fees, image, event_id))
                else:
                    db.execute('UPDATE events SET title=?, description=?, event_date=?, event_time=?, venue=?, fees=? WHERE id=?',
                               (title, description, event_date, event_time, venue, fees, event_id))
            else:
                db.execute('UPDATE events SET title=?, description=?, event_date=?, event_time=?, venue=?, fees=? WHERE id=?',
                           (title, description, event_date, event_time, venue, fees, event_id))
            db.commit()
            flash('Event updated!', 'success')

        elif action == 'toggle':
            db.execute('UPDATE events SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?', (event_id,))
            db.commit()
            flash('Event status toggled.', 'success')

        elif action == 'delete':
            db.execute('DELETE FROM events WHERE id = ?', (event_id,))
            db.execute('DELETE FROM event_registrations WHERE event_id = ?', (event_id,))
            db.commit()
            flash('Event deleted.', 'success')

        return redirect(url_for('manage_events'))

    all_events = db.execute('SELECT * FROM events ORDER BY event_date DESC').fetchall()
    return render_template('manage_events.html', events=all_events)


@app.route('/manage-settings', methods=['GET', 'POST'])
@admin_required
def manage_settings():
    db = get_db()

    if request.method == 'POST':
        fields = ['studio_name', 'tagline', 'phone', 'whatsapp', 'email',
                  'address', 'working_hours', 'instagram', 'facebook',
                  'youtube', 'about_text', 'admin_email', 'admin_phone']
        for field in fields:
            value = request.form.get(field, '').strip()
            existing = db.execute('SELECT key FROM site_settings WHERE key = ?', (field,)).fetchone()
            if existing:
                db.execute('UPDATE site_settings SET value = ? WHERE key = ?', (value, field))
            else:
                db.execute('INSERT INTO site_settings (key, value) VALUES (?, ?)', (field, value))
        db.commit()
        flash('Site settings updated successfully!', 'success')
        return redirect(url_for('manage_settings'))

    settings = get_settings()
    return render_template('manage_settings.html', settings=settings)


@app.route('/generate-template', methods=['GET', 'POST'])
@admin_required
def generate_template():
    db = get_db()
    generated_html = None

    if request.method == 'POST':
        template_type = request.form.get('template_type', 'offer')
        style = request.form.get('style', 'elegant')
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        description = request.form.get('description', '').strip()
        highlight = request.form.get('highlight', '').strip()
        date_text = request.form.get('date_text', '').strip()
        cta_text = request.form.get('cta_text', 'Book Now').strip()
        phone = request.form.get('phone', '+91 98765 43210').strip()
        address = request.form.get('address', 'JMD Makeover Studio').strip()
        link_url = request.form.get('link_url', '').strip()

        # Build QR code URL (free API, no library needed)
        import urllib.parse
        qr_data = link_url if link_url else request.host_url.rstrip('/')
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(qr_data)}"

        # Color schemes per style
        schemes = {
            'elegant': {
                'bg': '#1a1a1a', 'accent': '#B76E79', 'accent2': '#D4A574',
                'text': '#FFF8F0', 'text2': '#CCC', 'card_bg': 'rgba(255,248,240,0.06)',
                'gradient': 'linear-gradient(135deg, #1a1a1a 0%, #2d1f22 50%, #1a1a1a 100%)',
            },
            'rose': {
                'bg': '#FFF8F0', 'accent': '#B76E79', 'accent2': '#8E4A55',
                'text': '#1a1a1a', 'text2': '#555', 'card_bg': 'rgba(183,110,121,0.08)',
                'gradient': 'linear-gradient(135deg, #FFF8F0 0%, #FFE4E1 50%, #FFF8F0 100%)',
            },
            'bold': {
                'bg': '#0a0a0a', 'accent': '#FFD700', 'accent2': '#FF6B6B',
                'text': '#FFFFFF', 'text2': '#AAA', 'card_bg': 'rgba(255,215,0,0.08)',
                'gradient': 'linear-gradient(135deg, #0a0a0a 0%, #1a0a0a 50%, #0a0a0a 100%)',
            },
            'festive': {
                'bg': '#1a0520', 'accent': '#FF69B4', 'accent2': '#FFD700',
                'text': '#FFFFFF', 'text2': '#DDD', 'card_bg': 'rgba(255,105,180,0.1)',
                'gradient': 'linear-gradient(135deg, #1a0520 0%, #2d0a3e 50%, #1a0520 100%)',
            },
            'minimal': {
                'bg': '#FFFFFF', 'accent': '#333333', 'accent2': '#B76E79',
                'text': '#1a1a1a', 'text2': '#666', 'card_bg': '#F8F9FA',
                'gradient': 'linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%)',
            },
        }
        s = schemes.get(style, schemes['elegant'])

        # Type icons
        icons = {
            'offer': '🎉', 'course': '🎓', 'event': '✨',
            'service': '💄', 'announcement': '📢'
        }
        icon = icons.get(template_type, '✨')

        generated_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - JMD Makeover Studio</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:{s['gradient']};min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;color:{s['text']}}}
.flyer{{max-width:600px;width:100%;background:{s['card_bg']};border:1px solid rgba(255,255,255,0.1);border-radius:24px;overflow:hidden;position:relative;backdrop-filter:blur(10px)}}
.flyer-header{{padding:48px 40px 32px;text-align:center;position:relative}}
.flyer-header::before{{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:80px;height:4px;background:linear-gradient(90deg,{s['accent']},{s['accent2']});border-radius:2px}}
.brand{{font-family:'Playfair Display',serif;font-size:1rem;color:{s['accent']};letter-spacing:3px;text-transform:uppercase;margin-bottom:24px;display:block}}
.icon{{font-size:3rem;margin-bottom:16px;display:block}}
h1{{font-family:'Playfair Display',serif;font-size:2.2rem;font-weight:700;line-height:1.2;margin-bottom:12px}}
.subtitle{{font-size:1.05rem;color:{s['text2']};margin-bottom:8px}}
.highlight-badge{{display:inline-block;padding:10px 28px;background:linear-gradient(135deg,{s['accent']},{s['accent2']});color:#fff;font-size:1.3rem;font-weight:700;border-radius:50px;margin:20px 0;font-family:'Playfair Display',serif;box-shadow:0 8px 24px rgba(0,0,0,0.2)}}
.flyer-body{{padding:0 40px 32px;text-align:center}}
.description{{font-size:1rem;line-height:1.8;color:{s['text2']};margin-bottom:24px}}
.date-info{{display:inline-flex;align-items:center;gap:8px;padding:10px 24px;background:{s['card_bg']};border:1px solid rgba(255,255,255,0.08);border-radius:12px;font-size:0.9rem;color:{s['text']};margin-bottom:24px}}
.cta-btn{{display:inline-block;padding:16px 40px;background:linear-gradient(135deg,{s['accent']},{s['accent2']});color:#fff;font-size:1rem;font-weight:600;border-radius:50px;text-decoration:none;transition:all 0.3s;box-shadow:0 4px 16px rgba(0,0,0,0.2)}}
.cta-btn:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,0.3)}}
.qr-section{{padding:28px 40px;text-align:center;border-top:1px solid rgba(255,255,255,0.06)}}
.qr-section img{{width:140px;height:140px;border-radius:12px;padding:8px;background:rgba(255,255,255,0.92);display:inline-block;box-shadow:0 4px 16px rgba(0,0,0,0.15)}}
.qr-section p{{font-size:0.8rem;color:{s['text2']};margin-top:10px;letter-spacing:0.5px}}
.flyer-footer{{padding:20px 40px;border-top:1px solid rgba(255,255,255,0.06);text-align:center}}
.contact{{font-size:0.85rem;color:{s['text2']};line-height:1.8}}
.contact strong{{color:{s['accent']}}}
.sparkle{{position:absolute;width:6px;height:6px;background:{s['accent']};border-radius:50%;opacity:0.3}}
.sparkle:nth-child(1){{top:15%;left:10%;animation:pulse 3s infinite}}
.sparkle:nth-child(2){{top:25%;right:12%;animation:pulse 3s infinite 1s}}
.sparkle:nth-child(3){{bottom:30%;left:8%;animation:pulse 3s infinite 2s}}
.sparkle:nth-child(4){{top:60%;right:6%;animation:pulse 3s infinite 0.5s}}
@keyframes pulse{{0%,100%{{opacity:0.2;transform:scale(1)}}50%{{opacity:0.6;transform:scale(1.5)}}}}
@media(max-width:480px){{.flyer-header,.flyer-body,.flyer-footer{{padding-left:24px;padding-right:24px}}h1{{font-size:1.75rem}}.highlight-badge{{font-size:1.1rem;padding:8px 20px}}}}
</style>
</head>
<body>
<div class="flyer">
<div class="sparkle"></div><div class="sparkle"></div><div class="sparkle"></div><div class="sparkle"></div>
<div class="flyer-header">
<span class="brand">JMD Makeover Studio</span>
<span class="icon">{icon}</span>
<h1>{title}</h1>
{"<p class='subtitle'>" + subtitle + "</p>" if subtitle else ""}
{"<div class='highlight-badge'>" + highlight + "</div>" if highlight else ""}
</div>
<div class="flyer-body">
{"<p class='description'>" + description + "</p>" if description else ""}
{"<div class='date-info'>📅 " + date_text + "</div><br>" if date_text else ""}
<a href="{qr_data}" class="cta-btn">{cta_text}</a>
</div>
<div class="qr-section">
<img src="{qr_url}" alt="Scan for details">
<p>📱 Scan QR Code for full details</p>
</div>
<div class="flyer-footer">
<p class="contact">
<strong>📞 {phone}</strong><br>
📍 {address}
</p>
</div>
</div>
</body>
</html>'''

        flash('Template generated! Preview it below and copy the HTML.', 'success')

    # Fetch existing offers and courses for quick-fill
    offers_list = db.execute('SELECT * FROM offers WHERE is_active = 1 ORDER BY id DESC').fetchall()
    courses_list = db.execute('SELECT * FROM courses WHERE is_active = 1 ORDER BY id DESC').fetchall()

    return render_template('generate_template.html',
                           generated_html=generated_html,
                           offers=offers_list, courses=courses_list)


@app.route('/preview-template', methods=['POST'])
@admin_required
def preview_template():
    html = request.form.get('html_content', '')
    return html


# ═══════════════════════════════════════════════════════════════
#  RUN APP
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\n{'='*50}")
    print(f"  JMD Makeover Studio is running!")
    print(f"  Local:   http://127.0.0.1:5000")
    print(f"  Network: http://{local_ip}:5000")
    print(f"{'='*50}\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
