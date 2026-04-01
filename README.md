# ShopKart — Full Stack eCommerce

FastAPI + Jinja2 + SQLite + Django Admin + Razorpay + Stripe + Auth + Wishlist + Tracking

## Run

```bash
pip install -r requirements.txt
python start.py
```

## URLs

| URL | Page |
|-----|------|
| http://localhost:8000 | Website |
| http://localhost:8000/login | Login |
| http://localhost:8000/signup | Sign Up |
| http://localhost:8000/forgot-password | Forgot Password |
| http://localhost:8000/profile | User Profile + Addresses |
| http://localhost:8000/wishlist | Wishlist |
| http://localhost:8000/orders | My Orders |
| http://localhost:8000/orders/{id} | Order Tracking |
| http://localhost:8000/docs | FastAPI Swagger |
| http://localhost:8001/admin | Django Admin (admin/admin123) |

## Razorpay Setup

1. https://razorpay.com se Test Keys lo
2. main.py mein update karo: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
3. pip install razorpay

## Stripe Setup

1. https://stripe.com se Test Keys lo
2. main.py mein: STRIPE_PUBLIC_KEY update karo

## Email Setup

app/email_service.py mein:
- SMTP_USER = "your-gmail@gmail.com"
- SMTP_PASSWORD = "gmail-app-password"
- EMAIL_ENABLED = True

## Features

- Login / Signup / Logout (session-based)
- Forgot Password + Reset Password (email token)
- User Profile (edit details + saved addresses)
- Wishlist (heart button on every product)
- Cart (works for guests + logged in users)
- Checkout: Razorpay (UPI/Cards/EMI) + Stripe + COD
- Order History + Live Tracking Timeline
- Email notifications: Welcome + Order Confirmation + Password Reset
- Django Admin: Full management of Products, Categories, Orders, Users
