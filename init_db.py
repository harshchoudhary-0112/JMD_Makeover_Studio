import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = 'jmd_studio.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Services table
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL,
        duration TEXT,
        image TEXT,
        is_active INTEGER DEFAULT 1
    )''')

    # Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        service_id INTEGER,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        message TEXT,
        status TEXT DEFAULT 'Pending',
        admin_note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        duration TEXT,
        fees REAL,
        image TEXT,
        is_active INTEGER DEFAULT 1
    )''')

    # Course registrations table
    c.execute('''CREATE TABLE IF NOT EXISTS course_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        course_id INTEGER,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        admin_note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Offers table
    c.execute('''CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        discount TEXT,
        start_date TEXT,
        end_date TEXT,
        image TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Offer registrations table
    c.execute('''CREATE TABLE IF NOT EXISTS offer_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        offer_id INTEGER,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Gallery table
    c.execute('''CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image TEXT NOT NULL,
        caption TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Notifications table
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        type TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Contact inquiries table
    c.execute('''CREATE TABLE IF NOT EXISTS contact_inquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        subject TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- Seed Data ---

    # Default admin account
    admin_email = 'admin@jmd.com'
    c.execute('SELECT id FROM admins WHERE email = ?', (admin_email,))
    if not c.fetchone():
        admin_password = generate_password_hash('admin123')
        c.execute('INSERT INTO admins (email, password) VALUES (?, ?)',
                  (admin_email, admin_password))
        print(f'Default admin created: {admin_email} / admin123')

    # Sample services
    c.execute('SELECT COUNT(*) FROM services')
    if c.fetchone()[0] == 0:
        services = [
            ('Bridal Makeup', 'Complete bridal makeup package with HD finish, false lashes, and setting spray for your special day.', 15000, '2-3 hours', None, 1),
            ('Party Makeup', 'Glamorous party look with contouring, eye makeup, and lip styling.', 3500, '1 hour', None, 1),
            ('Hair Styling', 'Professional hair styling including curls, straightening, braids, and updos.', 2000, '45 mins', None, 1),
            ('Facial Treatment', 'Deep cleansing facial with premium products for glowing skin.', 1500, '1 hour', None, 1),
            ('Nail Art', 'Creative nail art designs with gel polish and nail extensions.', 800, '45 mins', None, 1),
            ('Pre-Bridal Package', 'Complete pre-bridal skincare and grooming package spread across multiple sessions.', 25000, '4-5 sessions', None, 1),
            ('Mehendi Design', 'Intricate traditional and modern mehendi designs for all occasions.', 2500, '1-2 hours', None, 1),
            ('Hair Color & Highlights', 'Professional hair coloring, highlights, and balayage services.', 3000, '2 hours', None, 1),
        ]
        c.executemany('INSERT INTO services (name, description, price, duration, image, is_active) VALUES (?, ?, ?, ?, ?, ?)', services)
        print('Sample services added')

    # Sample courses
    c.execute('SELECT COUNT(*) FROM courses')
    if c.fetchone()[0] == 0:
        courses = [
            ('Professional Makeup Artistry', 'Comprehensive 3-month course covering bridal, party, editorial, and fashion makeup techniques.', '3 Months', 45000, None, 1),
            ('Hair Styling Diploma', 'Learn cutting, coloring, styling, and treatment techniques from industry experts.', '6 Months', 60000, None, 1),
            ('Nail Art Certificate', 'Master gel extensions, nail art designs, and manicure/pedicure techniques.', '1 Month', 15000, None, 1),
            ('Basic Beauty Course', 'Foundation course covering skincare, basic makeup, threading, and waxing.', '2 Months', 25000, None, 1),
        ]
        c.executemany('INSERT INTO courses (title, description, duration, fees, image, is_active) VALUES (?, ?, ?, ?, ?, ?)', courses)
        print('Sample courses added')

    # Sample offers
    c.execute('SELECT COUNT(*) FROM offers')
    if c.fetchone()[0] == 0:
        offers = [
            ('Summer Special', 'Get 20% off on all facial treatments this summer!', '20% OFF', '2026-06-01', '2026-08-31', None, 1),
            ('Bridal Season Offer', 'Book bridal package and get free pre-bridal consultation.', 'Free Consultation', '2026-06-01', '2026-12-31', None, 1),
        ]
        c.executemany('INSERT INTO offers (title, description, discount, start_date, end_date, image, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)', offers)
        print('Sample offers added')

    conn.commit()
    conn.close()
    print('Database initialized successfully!')

if __name__ == '__main__':
    init_db()
