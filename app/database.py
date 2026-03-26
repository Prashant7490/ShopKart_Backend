from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.models import Base, Category, Product
import os
import sqlite3

# DB hamesha main.py ke saath wali folder mein banega
_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_FILE     = os.path.join(_BASE_DIR, "shopkart.db")
DATABASE_URL = "sqlite+aiosqlite:///" + _DB_FILE

engine            = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def _check_and_reset_db_sync():
    """
    Startup pe synchronously DB schema check karo.
    Builtin sqlite3 use karta hai — SQLAlchemy engine se koi conflict nahi.
    Agar koi required column missing ho toh purani DB delete kar deta hai.
    """
    if not os.path.exists(_DB_FILE):
        return

    required = {
        "users":    ["hashed_password", "phone", "is_active", "created_at"],
        "products": ["image_url", "is_featured", "free_delivery", "assured"],
        "orders":   ["session_id", "items", "total_amount", "payment_method"],
    }

    try:
        conn = sqlite3.connect(_DB_FILE)
        cur  = conn.cursor()
        needs_reset = False

        for table, cols in required.items():
            cur.execute("PRAGMA table_info(" + table + ")")
            existing = {row[1] for row in cur.fetchall()}
            if not existing:
                needs_reset = True
                break
            missing = [c for c in cols if c not in existing]
            if missing:
                print("[DB] Schema purana hai! Table '" + table + "' missing cols: " + str(missing))
                needs_reset = True
                break

        conn.close()

        if needs_reset:
            print("[DB] Purani DB delete ho rahi hai...")
            os.remove(_DB_FILE)
            print("[DB] Fresh DB startup pe banegi.")

    except Exception as e:
        print("[DB] Schema check error: " + str(e))
        try:
            os.remove(_DB_FILE)
        except Exception:
            pass


def _upgrade_db_schema_sync():
    """
    Existing SQLite DB ko safe tareeke se upgrade karo.
    Missing columns ko add karta hai, puri DB delete nahi karta.
    """
    if not os.path.exists(_DB_FILE):
        return

    migrations = {
        "users": {
            "phone": "ALTER TABLE users ADD COLUMN phone VARCHAR(15) NOT NULL DEFAULT ''",
            "hashed_password": "ALTER TABLE users ADD COLUMN hashed_password VARCHAR NOT NULL DEFAULT ''",
            "is_active": "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
            "created_at": "ALTER TABLE users ADD COLUMN created_at DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        },
        "products": {
            "image_url": "ALTER TABLE products ADD COLUMN image_url VARCHAR NOT NULL DEFAULT ''",
            "is_featured": "ALTER TABLE products ADD COLUMN is_featured BOOLEAN NOT NULL DEFAULT 0",
            "free_delivery": "ALTER TABLE products ADD COLUMN free_delivery BOOLEAN NOT NULL DEFAULT 0",
            "assured": "ALTER TABLE products ADD COLUMN assured BOOLEAN NOT NULL DEFAULT 0",
        },
        "orders": {
            "session_id": "ALTER TABLE orders ADD COLUMN session_id VARCHAR(100) NOT NULL DEFAULT ''",
            "items": "ALTER TABLE orders ADD COLUMN items JSON NOT NULL DEFAULT '[]'",
            "address": "ALTER TABLE orders ADD COLUMN address JSON NOT NULL DEFAULT '{}'",
            "payment_method": "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(50) NOT NULL DEFAULT 'cod'",
            "payment_id": "ALTER TABLE orders ADD COLUMN payment_id VARCHAR NOT NULL DEFAULT ''",
            "razorpay_order_id": "ALTER TABLE orders ADD COLUMN razorpay_order_id VARCHAR NOT NULL DEFAULT ''",
            "payment_status": "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(50) NOT NULL DEFAULT 'pending'",
            "status": "ALTER TABLE orders ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Confirmed'",
            "total_amount": "ALTER TABLE orders ADD COLUMN total_amount FLOAT NOT NULL DEFAULT 0",
            "created_at": "ALTER TABLE orders ADD COLUMN created_at DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        },
        "wishlist": {
            "added_at": "ALTER TABLE wishlist ADD COLUMN added_at DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        },
        "addresses": {
            "name": "ALTER TABLE addresses ADD COLUMN name VARCHAR(150) NOT NULL DEFAULT ''",
            "phone": "ALTER TABLE addresses ADD COLUMN phone VARCHAR(15) NOT NULL DEFAULT ''",
            "street": "ALTER TABLE addresses ADD COLUMN street VARCHAR(300) NOT NULL DEFAULT ''",
            "city": "ALTER TABLE addresses ADD COLUMN city VARCHAR(100) NOT NULL DEFAULT ''",
            "state": "ALTER TABLE addresses ADD COLUMN state VARCHAR(100) NOT NULL DEFAULT ''",
            "pincode": "ALTER TABLE addresses ADD COLUMN pincode VARCHAR(10) NOT NULL DEFAULT ''",
            "is_default": "ALTER TABLE addresses ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT 0",
        },
        "password_reset_tokens": {
            "used": "ALTER TABLE password_reset_tokens ADD COLUMN used BOOLEAN NOT NULL DEFAULT 0",
        },
    }

    conn = None
    try:
        conn = sqlite3.connect(_DB_FILE)
        cur = conn.cursor()

        for table, columns in migrations.items():
            cur.execute("PRAGMA table_info(" + table + ")")
            existing = {row[1] for row in cur.fetchall()}
            if not existing:
                continue

            for column, ddl in columns.items():
                if column not in existing:
                    print("[DB] Table '" + table + "' mein missing column add ho raha hai: " + column)
                    cur.execute(ddl)

        conn.commit()
    except Exception as e:
        print("[DB] Schema upgrade error: " + str(e))
    finally:
        if conn is not None:
            conn.close()


async def init_db():
    _upgrade_db_schema_sync()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()


async def seed_data():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Category))
        if result.scalars().first():
            return

        categories = [
            Category(id="electronics", name="Electronics",    icon="📱", image_url="https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400"),
            Category(id="fashion",     name="Fashion",        icon="👗", image_url="https://images.unsplash.com/photo-1483985988355-763728e1935b?w=400"),
            Category(id="home",        name="Home & Kitchen", icon="🏠", image_url="https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400"),
            Category(id="books",       name="Books",          icon="📚", image_url="https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400"),
            Category(id="sports",      name="Sports",         icon="⚽", image_url="https://images.unsplash.com/photo-1461897104016-0b3b00cc81ee?w=400"),
            Category(id="beauty",      name="Beauty",         icon="💄", image_url="https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400"),
        ]
        db.add_all(categories)

        products = [
            Product(id="P001", name="Samsung Galaxy S24 Ultra 5G",
                description="200MP camera, Snapdragon 8 Gen 3, 5000mAh battery, built-in S Pen.",
                price=124999, original_price=134999, discount_percent=7, category="electronics",
                brand="Samsung", rating=4.6, review_count=12845, sold_count=45000, stock=89,
                image_url="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500",
                images=["https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500"],
                tags=["5g","flagship","camera"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P002", name="Apple iPhone 15 Pro Max 256GB",
                description="A17 Pro chip, 48MP main camera with 5x optical zoom, USB-C.",
                price=159900, original_price=179900, discount_percent=11, category="electronics",
                brand="Apple", rating=4.7, review_count=23412, sold_count=67000, stock=43,
                image_url="https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=500",
                images=["https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=500"],
                tags=["iphone","apple","5g"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P003", name="Sony WH-1000XM5 Wireless Headphones",
                description="Industry-leading noise cancellation, 30-hour battery life.",
                price=24990, original_price=34990, discount_percent=29, category="electronics",
                brand="Sony", rating=4.5, review_count=8921, sold_count=28000, stock=156,
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500",
                images=["https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"],
                tags=["headphones","anc","wireless"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P004", name="MacBook Air M3 13-inch",
                description="M3 chip, 18-hour battery, 13.6-inch Liquid Retina display.",
                price=114900, original_price=124900, discount_percent=8, category="electronics",
                brand="Apple", rating=4.8, review_count=5432, sold_count=19000, stock=23,
                image_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500",
                images=["https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500"],
                tags=["laptop","mac","apple"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P005", name="boAt Rockerz 450 Bluetooth Headphone",
                description="40-hour playback, fast charging, 40mm drivers.",
                price=1299, original_price=3990, discount_percent=67, category="electronics",
                brand="boAt", rating=4.1, review_count=234521, sold_count=890000, stock=5000,
                image_url="https://images.unsplash.com/photo-1572536147248-ac59a8abfa4b?w=500",
                images=["https://images.unsplash.com/photo-1572536147248-ac59a8abfa4b?w=500"],
                tags=["headphones","bluetooth","budget"], is_featured=False, free_delivery=False, assured=True),
            Product(id="P006", name="Nike Air Max 270 Running Shoes",
                description="Large Max Air unit for all-day comfort with bold look.",
                price=8995, original_price=12995, discount_percent=31, category="fashion",
                brand="Nike", rating=4.4, review_count=18923, sold_count=56000, stock=234,
                image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
                images=["https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"],
                tags=["shoes","nike","running"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P007", name="Levi's 511 Slim Fit Jeans",
                description="Slim through the seat and thigh, narrow leg opening.",
                price=2699, original_price=5999, discount_percent=55, category="fashion",
                brand="Levi's", rating=4.3, review_count=45231, sold_count=120000, stock=890,
                image_url="https://images.unsplash.com/photo-1542272604-787c3835535d?w=500",
                images=["https://images.unsplash.com/photo-1542272604-787c3835535d?w=500"],
                tags=["jeans","denim","levis"], is_featured=False, free_delivery=True, assured=True),
            Product(id="P008", name="Instant Pot Duo 7-in-1 Pressure Cooker",
                description="7-in-1 multi-cooker: pressure cooker, slow cooker, rice cooker.",
                price=8499, original_price=12999, discount_percent=35, category="home",
                brand="Instant Pot", rating=4.6, review_count=89012, sold_count=230000, stock=345,
                image_url="https://images.unsplash.com/photo-1585515320310-259814833e62?w=500",
                images=["https://images.unsplash.com/photo-1585515320310-259814833e62?w=500"],
                tags=["kitchen","cooker","appliance"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P009", name="Atomic Habits by James Clear",
                description="No.1 NYT bestseller. Build good habits and break bad ones.",
                price=349, original_price=799, discount_percent=56, category="books",
                brand="Penguin", rating=4.7, review_count=156789, sold_count=450000, stock=9999,
                image_url="https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=500",
                images=["https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=500"],
                tags=["self-help","habits","bestseller"], is_featured=True, free_delivery=False, assured=True),
            Product(id="P010", name='LG 55" 4K OLED Smart TV C3',
                description="OLED evo panel, Dolby Vision & Atmos, 4K@120Hz gaming.",
                price=129990, original_price=179990, discount_percent=28, category="electronics",
                brand="LG", rating=4.7, review_count=4512, sold_count=12000, stock=34,
                image_url="https://images.unsplash.com/photo-1593784991095-a205069470b6?w=500",
                images=["https://images.unsplash.com/photo-1593784991095-a205069470b6?w=500"],
                tags=["tv","oled","4k"], is_featured=True, free_delivery=True, assured=True),
            Product(id="P011", name="Yoga Mat Premium Anti-Slip 6mm",
                description="TPE yoga mat, alignment lines, non-slip, eco-friendly.",
                price=799, original_price=1999, discount_percent=60, category="sports",
                brand="FitKart", rating=4.2, review_count=32456, sold_count=78000, stock=1200,
                image_url="https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=500",
                images=["https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=500"],
                tags=["yoga","fitness","mat"], is_featured=False, free_delivery=False, assured=False),
            Product(id="P012", name="Lakme 9 to 5 Weightless Foundation SPF 25",
                description="Buildable coverage, SPF 25, lasts 16 hours.",
                price=525, original_price=750, discount_percent=30, category="beauty",
                brand="Lakme", rating=4.0, review_count=67234, sold_count=198000, stock=4500,
                image_url="https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500",
                images=["https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500"],
                tags=["makeup","foundation","beauty"], is_featured=False, free_delivery=False, assured=True),
        ]
        db.add_all(products)
        await db.commit()
        print("✅ Database seeded!")
