#!/usr/bin/env python
"""
ShopKart - FastAPI + Django Admin dono ek saath start!
Usage: python start.py
"""
import subprocess, sys, os, time, threading, socket, sqlite3

ROOT       = os.path.dirname(os.path.abspath(__file__))
DJANGO_DIR = os.path.join(ROOT, 'django_admin')


def is_port_free(port):
    """Check karo port available hai ya nahi"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def find_free_port(start=8001):
    """Pehla available port dhundo"""
    for port in range(start, start + 20):
        if is_port_free(port):
            return port
    return start


def check_and_fix_db():
    """
    DB schema validate karo. Agar purana schema hai (missing columns),
    toh automatically delete karke fresh DB banao.
    """
    db_path = os.path.join(ROOT, 'shopkart.db')
    if not os.path.exists(db_path):
        return  # nahi hai toh app startup pe khud banega

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Required columns check karo
        required = {
            'users':    ['id','name','email','phone','hashed_password','is_active','created_at'],
            'products': ['id','name','price','category','image_url','is_featured'],
            'orders':   ['id','user_id','session_id','items','total_amount','status'],
        }

        needs_reset = False
        for table, cols in required.items():
            try:
                cursor.execute(f'PRAGMA table_info({table})')
                existing = {row[1] for row in cursor.fetchall()}
                if not existing:
                    needs_reset = True
                    break
                missing = [c for c in cols if c not in existing]
                if missing:
                    print(f"  ⚠️  DB schema purana hai — missing columns: {missing}")
                    needs_reset = True
                    break
            except Exception:
                needs_reset = True
                break

        conn.close()

        if needs_reset:
            print("  🔄 Purani DB delete ho rahi hai — fresh database ban rahi hai...")
            os.remove(db_path)
            print("  ✅ Fresh DB ready hogi jab server start hoga.")

    except Exception as e:
        print(f"  ⚠️  DB check failed: {e}")


def setup_django():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'shopkart_admin.settings'
    sys.path.insert(0, DJANGO_DIR)
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0)
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@shopkart.com', 'admin123')
        print("  ✅ Superuser created: admin / admin123")


def run_fastapi(port):
    print(f"  🚀 FastAPI starting on port {port}...")
    subprocess.run([
        sys.executable, '-m', 'uvicorn', 'main:app',
        '--reload', '--port', str(port), '--host', '127.0.0.1'
    ], cwd=ROOT)


def run_django(port):
    print(f"  🔧 Django Admin starting on port {port}...")
    subprocess.run(
        [sys.executable, 'manage.py', 'runserver', str(port), '--noreload'],
        cwd=DJANGO_DIR,
        env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'shopkart_admin.settings'}
    )


if __name__ == '__main__':
    print("=" * 60)
    print("  ShopKart — FastAPI + Django Admin + Auth + Payments")
    print("=" * 60)

    print(f"\n  Checking ports...")

    # FastAPI ke liye free port dhundo (8000 se shuru)
    fastapi_port = find_free_port(8000)
    if fastapi_port != 8000:
        print(f"  ⚠️  Port 8000 busy hai — automatically port {fastapi_port} use ho raha hai.")
    else:
        print(f"  ✅ FastAPI  → port {fastapi_port}")

    # Django ke liye alag free port dhundo
    django_port = find_free_port(fastapi_port + 1)
    print(f"  ✅ Django   → port {django_port}")

    check_and_fix_db()
    setup_django()

    print()
    print(f"  🌐 Website      : http://localhost:{fastapi_port}")
    print(f"  📋 Swagger Docs : http://localhost:{fastapi_port}/docs")
    print(f"  🔧 Django Admin : http://localhost:{django_port}/admin  (admin/admin123)")
    print()
    print("  📄 Pages: /login  /signup  /forgot-password")
    print("            /profile  /wishlist  /orders  /cart")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)

    t1 = threading.Thread(target=run_fastapi, args=(fastapi_port,), daemon=True)
    t2 = threading.Thread(target=run_django,  args=(django_port,),  daemon=True)

    t1.start()
    time.sleep(3)   # FastAPI ko pehle start hone do
    t2.start()

    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("\n\n  🛑 Servers stopped. Bye!")
