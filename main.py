from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
import uuid, hmac, hashlib
import random
from datetime import datetime, timedelta

from app.database     import get_db, init_db
from app.models       import Product, Category, Order, User, Wishlist, Address, PasswordResetToken
from app.schemas      import CartItemIn
from app.auth         import (hash_password, verify_password, login_user, logout_user,
                               get_current_user, get_session_id,
                               generate_reset_token, verify_reset_token)
from app.email_service import (send_welcome_email, send_password_reset_email,
                                send_signup_otp_email,
                                send_order_confirmation_email)

# ── Config ────────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID     = "rzp_test_XXXXXXXXXXXXXXXX"   # apni key yahan dalo
RAZORPAY_KEY_SECRET = "XXXXXXXXXXXXXXXXXXXXXXXX"

app = FastAPI(title="ShopKart")
app.add_middleware(SessionMiddleware, secret_key="shopkart-secret-2024", max_age=86400 * 7)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Safe date helpers registered as Jinja2 globals — NOT in context dict
def fmt_date(dt) -> str:
    if not dt: return ""
    try: return dt.strftime("%d %B %Y")
    except: return str(dt)[:10]

def fmt_datetime(dt) -> str:
    if not dt: return ""
    try: return dt.strftime("%d %B %Y, %I:%M %p")
    except: return str(dt)[:16]

templates.env.globals["fmt_date"]     = fmt_date
templates.env.globals["fmt_datetime"] = fmt_datetime

cart_store: dict = {}
signup_otp_store: dict = {}


# ── Startup ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await init_db()


# ── Helpers ───────────────────────────────────────────────────────────────
def set_cookie(response, session_id: str):
    response.set_cookie("session_id", session_id, max_age=86400 * 7, httponly=True)


def get_cart(sid: str) -> list:
    return cart_store.get(sid, [])


def generate_signup_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def get_signup_payload(email: str):
    return signup_otp_store.get(email.lower().strip())


async def ctx(request: Request, db: AsyncSession) -> dict:
    """Base context for every page"""
    sid  = get_session_id(request)
    user = await get_current_user(request, db)
    cart = get_cart(sid)

    wishlist_ids = set()
    if user:
        wq = await db.execute(select(Wishlist.product_id).where(Wishlist.user_id == user.id))
        wishlist_ids = set(wq.scalars().all())

    return {
        "request":      request,
        "current_user": user,
        "cart_count":   len(cart),
        "wishlist_ids": wishlist_ids,
        "session_id":   sid,
    }


def tmpl(name: str, context: dict, sid: str = None):
    # Starlette 0.40+ mein TemplateResponse ka naya signature hai
    # request alag pass karna padta hai — dict unhashable hota tha pehle
    request = context.get("request")
    ctx_data = {k: v for k, v in context.items() if k != "request"}
    response = templates.TemplateResponse(request=request, name=name, context=ctx_data)
    if sid:
        set_cookie(response, sid)
    return response


# ══════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/", db: AsyncSession = Depends(get_db)):
    c = await ctx(request, db)
    if c["current_user"]:
        return RedirectResponse("/", status_code=302)
    c["next"] = next
    return tmpl("store/auth/login.html", c)


@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...), password: str = Form(...),
    next: str = Form(default="/"), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    user   = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        c = await ctx(request, db)
        c["error"] = "Invalid email or password"
        c["next"]  = next
        return tmpl("store/auth/login.html", c)
    login_user(request, user.id)
    return RedirectResponse(next if next.startswith("/") else "/", status_code=302)


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, db: AsyncSession = Depends(get_db)):
    c = await ctx(request, db)
    if c["current_user"]:
        return RedirectResponse("/", status_code=302)
    return tmpl("store/auth/signup.html", c)


@app.post("/signup", response_class=HTMLResponse)
async def signup_post(
    request: Request,
    name: str = Form(...), email: str = Form(...),
    phone: str = Form(default=""), password: str = Form(...),
    confirm_password: str = Form(...), db: AsyncSession = Depends(get_db),
):
    c = await ctx(request, db)
    name = name.strip()
    email = email.lower().strip()
    phone = phone.strip()
    if password != confirm_password:
        c["error"] = "Passwords do not match"
        c["form"] = {"name": name, "email": email, "phone": phone}
        return tmpl("store/auth/signup.html", c)
    if len(password) < 6:
        c["error"] = "Password must be at least 6 characters"
        c["form"] = {"name": name, "email": email, "phone": phone}
        return tmpl("store/auth/signup.html", c)
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        c["error"] = "Email already registered. Please login."
        c["form"] = {"name": name, "email": email, "phone": phone}
        return tmpl("store/auth/signup.html", c)

    otp = generate_signup_otp()
    signup_otp_store[email] = {
        "name": name,
        "email": email,
        "phone": phone,
        "hashed_password": hash_password(password),
        "otp": otp,
        "expires_at": datetime.now() + timedelta(minutes=10),
    }
    await send_signup_otp_email(email, name, otp)
    verify_context = await ctx(request, db)
    verify_context["email"] = email
    verify_context["masked_email"] = email[:2] + ("*" * max(len(email.split("@")[0]) - 2, 1)) + "@" + email.split("@", 1)[1]
    verify_context["success"] = "OTP sent to your email. Enter it below to complete signup."
    return tmpl("store/auth/verify_signup_otp.html", verify_context)


@app.get("/signup/verify-otp", response_class=HTMLResponse)
async def signup_verify_page(request: Request, email: str = "", db: AsyncSession = Depends(get_db)):
    c = await ctx(request, db)
    if c["current_user"]:
        return RedirectResponse("/", status_code=302)
    email = email.lower().strip()
    payload = get_signup_payload(email) if email else None
    if not payload:
        return RedirectResponse("/signup", status_code=302)
    c["email"] = email
    c["masked_email"] = email[:2] + ("*" * max(len(email.split("@")[0]) - 2, 1)) + "@" + email.split("@", 1)[1]
    return tmpl("store/auth/verify_signup_otp.html", c)


@app.post("/signup/verify-otp", response_class=HTMLResponse)
async def signup_verify_post(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    c = await ctx(request, db)
    if c["current_user"]:
        return RedirectResponse("/", status_code=302)

    email = email.lower().strip()
    otp = otp.strip()
    payload = get_signup_payload(email)
    c["email"] = email
    if "@" in email:
        c["masked_email"] = email[:2] + ("*" * max(len(email.split("@")[0]) - 2, 1)) + "@" + email.split("@", 1)[1]

    if not payload:
        c["error"] = "OTP expired or signup session not found. Please try again."
        return tmpl("store/auth/verify_signup_otp.html", c)

    if payload["expires_at"] < datetime.now():
        signup_otp_store.pop(email, None)
        c["error"] = "OTP expired. Please signup again."
        return tmpl("store/auth/verify_signup_otp.html", c)

    if payload["otp"] != otp:
        c["error"] = "Invalid OTP. Please try again."
        return tmpl("store/auth/verify_signup_otp.html", c)

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        signup_otp_store.pop(email, None)
        c["error"] = "Email already registered. Please login."
        return tmpl("store/auth/verify_signup_otp.html", c)

    user = User(
        id=str(uuid.uuid4()),
        name=payload["name"],
        email=payload["email"],
        phone=payload["phone"],
        hashed_password=payload["hashed_password"],
    )
    db.add(user)
    await db.commit()
    signup_otp_store.pop(email, None)
    login_user(request, user.id)
    await send_welcome_email(user.email, user.name)
    return RedirectResponse("/", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", status_code=302)


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_page(request: Request, db: AsyncSession = Depends(get_db)):
    return tmpl("store/auth/forgot_password.html", await ctx(request, db))


@app.post("/forgot-password", response_class=HTMLResponse)
async def forgot_post(request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)):
    c = await ctx(request, db)
    c["success"] = "If this email is registered, you will receive a reset link."
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    user   = result.scalar_one_or_none()
    if user:
        token = generate_reset_token(user.email)
        db.add(PasswordResetToken(
            id=str(uuid.uuid4()), user_id=user.id, token=token,
            expires_at=datetime.now() + timedelta(hours=1)
        ))
        await db.commit()
        await send_password_reset_email(user.email, user.name, token)
    return tmpl("store/auth/forgot_password.html", c)


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_page(request: Request, token: str = "", db: AsyncSession = Depends(get_db)):
    c = await ctx(request, db)
    if not verify_reset_token(token):
        c["error"] = "Link expired or invalid."
    else:
        c["token"] = token
    return tmpl("store/auth/reset_password.html", c)


@app.post("/reset-password", response_class=HTMLResponse)
async def reset_post(
    request: Request, token: str = Form(...),
    password: str = Form(...), confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    c = await ctx(request, db)
    c["token"] = token
    if password != confirm_password:
        c["error"] = "Passwords do not match"
        return tmpl("store/auth/reset_password.html", c)
    email = verify_reset_token(token)
    if not email:
        c["error"] = "Link expired. Request a new one."
        return tmpl("store/auth/reset_password.html", c)
    tok_q = await db.execute(select(PasswordResetToken).where(
        PasswordResetToken.token == token, PasswordResetToken.used == False))
    tok = tok_q.scalar_one_or_none()
    if not tok:
        c["error"] = "This link has already been used."
        return tmpl("store/auth/reset_password.html", c)
    user_q = await db.execute(select(User).where(User.email == email))
    user   = user_q.scalar_one_or_none()
    if user:
        user.hashed_password = hash_password(password)
    tok.used = True
    await db.commit()
    c["success"] = "Password reset! You can now login."
    c.pop("token", None)
    return tmpl("store/auth/reset_password.html", c)


# ══════════════════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════════════════

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    c    = await ctx(request, db)
    user = c["current_user"]
    if not user:
        return RedirectResponse("/login?next=/profile", status_code=302)
    orders_q = await db.execute(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(5))
    addrs_q  = await db.execute(select(Address).where(Address.user_id == user.id))
    c["recent_orders"] = orders_q.scalars().all()
    c["addresses"]     = addrs_q.scalars().all()
    c["updated"]       = request.query_params.get("updated")
    c["addr_saved"]    = request.query_params.get("addr")
    return tmpl("store/profile.html", c)


@app.post("/profile/update")
async def profile_update(
    request: Request, name: str = Form(...), phone: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    c    = await ctx(request, db)
    user = c["current_user"]
    if not user:
        return RedirectResponse("/login", status_code=302)
    user.name  = name.strip()
    user.phone = phone.strip()
    await db.commit()
    return RedirectResponse("/profile?updated=1", status_code=302)


@app.post("/profile/add-address")
async def add_address(
    request: Request,
    name: str = Form(...), phone: str = Form(...), street: str = Form(...),
    city: str = Form(...), state: str = Form(...), pincode: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    c    = await ctx(request, db)
    user = c["current_user"]
    if not user:
        return RedirectResponse("/login", status_code=302)
    db.add(Address(id=str(uuid.uuid4()), user_id=user.id,
                   name=name, phone=phone, street=street,
                   city=city, state=state, pincode=pincode))
    await db.commit()
    return RedirectResponse("/profile?addr=1", status_code=302)


# ══════════════════════════════════════════════════════════════════════════
#  WISHLIST
# ══════════════════════════════════════════════════════════════════════════

@app.get("/wishlist", response_class=HTMLResponse)
async def wishlist_page(request: Request, db: AsyncSession = Depends(get_db)):
    c    = await ctx(request, db)
    user = c["current_user"]
    if not user:
        return RedirectResponse("/login?next=/wishlist", status_code=302)
    wq       = await db.execute(
        select(Wishlist).where(Wishlist.user_id == user.id).order_by(Wishlist.added_at.desc()))
    items    = wq.scalars().all()
    prod_ids = [i.product_id for i in items]
    products = []
    if prod_ids:
        pq       = await db.execute(select(Product).where(Product.id.in_(prod_ids)))
        products = pq.scalars().all()
    c["wishlist_products"] = products
    cart     = get_cart(c["session_id"])
    c["cart_ids"] = {i["product_id"] for i in cart}
    return tmpl("store/wishlist.html", c)


@app.post("/api/wishlist/toggle")
async def toggle_wishlist(request: Request, db: AsyncSession = Depends(get_db)):
    data       = await request.json()
    product_id = data.get("product_id")
    c    = await ctx(request, db)
    user = c["current_user"]
    if not user:
        return JSONResponse({"error": "login_required"}, status_code=401)
    existing = await db.execute(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == product_id))
    item = existing.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
        return JSONResponse({"action": "removed"})
    db.add(Wishlist(id=str(uuid.uuid4()), user_id=user.id, product_id=product_id))
    await db.commit()
    return JSONResponse({"action": "added"})


# ══════════════════════════════════════════════════════════════════════════
#  MAIN PAGES
# ══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    c   = await ctx(request, db)
    sid = c["session_id"]
    feat_q = await db.execute(select(Product).where(Product.is_featured == True).limit(8))
    cats_q = await db.execute(select(Category))
    c["featured"]   = feat_q.scalars().all()
    c["categories"] = cats_q.scalars().all()
    cart            = get_cart(sid)
    c["cart_ids"]   = {i["product_id"] for i in cart}
    response = tmpl("store/home.html", c, sid)
    return response


@app.get("/products", response_class=HTMLResponse)
async def products_page(
    request: Request,
    category:  Optional[str]   = None,
    search:    Optional[str]   = None,
    sort_by:   Optional[str]   = "popularity",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    c   = await ctx(request, db)
    sid = c["session_id"]

    q = select(Product)
    if category:  q = q.where(Product.category == category)
    if search:    q = q.where(or_(Product.name.ilike(f"%{search}%"), Product.brand.ilike(f"%{search}%")))
    if min_price: q = q.where(Product.price >= min_price)
    if max_price: q = q.where(Product.price <= max_price)

    sort_map = {
        "price_asc":  Product.price.asc(),
        "price_desc": Product.price.desc(),
        "rating":     Product.rating.desc(),
        "popularity": Product.sold_count.desc(),
    }
    q = q.order_by(sort_map.get(sort_by or "popularity", Product.sold_count.desc()))

    result   = await db.execute(q)
    cats_q   = await db.execute(select(Category))
    cart     = get_cart(sid)
    cart_ids = {i["product_id"] for i in cart}

    c.update({
        "products":         result.scalars().all(),
        "categories":       cats_q.scalars().all(),
        "current_category": category or "",
        "current_search":   search or "",
        "current_sort":     sort_by or "popularity",
        "min_price":        min_price or "",
        "max_price":        max_price or "",
        "cart_ids":         cart_ids,
    })
    return tmpl("store/products.html", c, sid)


@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str, db: AsyncSession = Depends(get_db)):
    c   = await ctx(request, db)
    sid = c["session_id"]

    result  = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    related_q = await db.execute(
        select(Product).where(Product.category == product.category, Product.id != product.id).limit(4))
    cart     = get_cart(sid)
    cart_ids = {i["product_id"] for i in cart}

    c.update({
        "product":  product,
        "related":  related_q.scalars().all(),
        "cart_ids": cart_ids,
        "in_cart":  product_id in cart_ids,
    })
    return tmpl("store/product_detail.html", c, sid)


# ── Cart ──────────────────────────────────────────────────────────────────

@app.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, db: AsyncSession = Depends(get_db)):
    c          = await ctx(request, db)
    sid        = c["session_id"]
    cart_items = get_cart(sid)

    products_map = {}
    if cart_items:
        pids = [i["product_id"] for i in cart_items]
        pq   = await db.execute(select(Product).where(Product.id.in_(pids)))
        for p in pq.scalars().all():
            products_map[p.id] = p

    enriched, total = [], 0
    for item in cart_items:
        p = products_map.get(item["product_id"])
        if p:
            sub    = p.price * item["quantity"]
            total += sub
            enriched.append({"product": p, "quantity": item["quantity"], "subtotal": sub})

    delivery = 0 if total >= 499 else 40
    c.update({"cart_items": enriched, "total": round(total, 2),
               "delivery": delivery, "grand_total": round(total + delivery, 2)})
    return tmpl("store/cart.html", c, sid)


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    c   = await ctx(request, db)
    sid = c["session_id"]
    if not get_cart(sid):
        return RedirectResponse("/cart", status_code=302)

    pids = [i["product_id"] for i in get_cart(sid)]
    pq   = await db.execute(select(Product).where(Product.id.in_(pids)))
    pmap = {p.id: p for p in pq.scalars().all()}
    total    = sum(pmap[i["product_id"]].price * i["quantity"]
                   for i in get_cart(sid) if i["product_id"] in pmap)
    delivery = 0 if total >= 499 else 40

    addrs = []
    if c["current_user"]:
        aq    = await db.execute(select(Address).where(Address.user_id == c["current_user"].id))
        addrs = aq.scalars().all()

    c.update({"total": round(total, 2), "delivery": delivery,
               "grand_total": round(total + delivery, 2),
               "addresses": addrs, "razorpay_key_id": RAZORPAY_KEY_ID})
    return tmpl("store/checkout.html", c, sid)


@app.post("/checkout/place-order")
async def place_order(
    request: Request,
    name: str = Form(...), phone: str = Form(...),
    pincode: str = Form(...), street: str = Form(...),
    city: str = Form(...), state: str = Form(...),
    payment_method: str = Form(...),
    razorpay_payment_id: str   = Form(default=""),
    razorpay_order_id_val: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    c          = await ctx(request, db)
    sid        = c["session_id"]
    user       = c["current_user"]
    cart_items = get_cart(sid)
    if not cart_items:
        return RedirectResponse("/cart", status_code=302)

    pids     = [i["product_id"] for i in cart_items]
    pq       = await db.execute(select(Product).where(Product.id.in_(pids)))
    pmap     = {p.id: p for p in pq.scalars().all()}
    total    = sum(pmap[i["product_id"]].price * i["quantity"]
                   for i in cart_items if i["product_id"] in pmap)
    delivery = 0 if total >= 499 else 40

    oid = str(uuid.uuid4())[:8].upper()
    db.add(Order(
        id=oid, user_id=user.id if user else None, session_id=sid,
        items=cart_items,
        address={"name": name, "phone": phone, "pincode": pincode,
                 "street": street, "city": city, "state": state},
        payment_method=payment_method,
        payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id_val,
        payment_status="paid" if razorpay_payment_id else "pending",
        status="Confirmed",
        total_amount=round(total + delivery, 2),
        created_at=datetime.now(),
    ))
    await db.commit()
    cart_store.pop(sid, None)

    if user:
        await send_order_confirmation_email(user.email, user.name, oid, cart_items, total + delivery)

    return RedirectResponse(f"/orders?new={oid}", status_code=302)


# ── Orders ────────────────────────────────────────────────────────────────

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, new: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    c    = await ctx(request, db)
    sid  = c["session_id"]
    user = c["current_user"]

    if user:
        oq = await db.execute(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()))
    else:
        oq = await db.execute(
            select(Order).where(Order.session_id == sid).order_by(Order.created_at.desc()))

    orders = oq.scalars().all()
    # Add formatted date as attribute-safe strings
    for o in orders:
        o._fmt_date = fmt_datetime(o.created_at)

    c["orders"]       = orders
    c["new_order_id"] = new
    return tmpl("store/orders.html", c)


@app.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(request: Request, order_id: str, db: AsyncSession = Depends(get_db)):
    c      = await ctx(request, db)
    result = await db.execute(select(Order).where(Order.id == order_id))
    order  = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    pids = [i["product_id"] for i in order.items]
    pq   = await db.execute(select(Product).where(Product.id.in_(pids)))
    pmap = {p.id: p for p in pq.scalars().all()}
    enriched = [{"product": pmap.get(i["product_id"]), "quantity": i["quantity"]}
                for i in order.items if i["product_id"] in pmap]

    c["order"]      = order
    c["order_items"] = enriched
    c["order_date"]  = fmt_datetime(order.created_at)
    c["tracking_steps"] = [
        {"label": "Order Confirmed",  "done": True},
        {"label": "Processing",       "done": order.status in ["Processing","Shipped","Delivered"]},
        {"label": "Shipped",          "done": order.status in ["Shipped","Delivered"]},
        {"label": "Out for Delivery", "done": order.status == "Delivered"},
        {"label": "Delivered",        "done": order.status == "Delivered"},
    ]
    return tmpl("store/order_detail.html", c)


# ── Razorpay ──────────────────────────────────────────────────────────────

@app.post("/api/razorpay/create-order")
async def razorpay_create_order(request: Request):
    data  = await request.json()
    total = int(float(data.get("amount", 0))) * 100
    try:
        import razorpay
        client   = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        rz_order = client.order.create({"amount": total, "currency": "INR",
                                         "receipt": "rcp_" + str(uuid.uuid4())[:8]})
        return JSONResponse({"razorpay_order_id": rz_order["id"],
                             "amount": total, "key": RAZORPAY_KEY_ID})
    except Exception:
        mock_id = "order_mock_" + str(uuid.uuid4())[:10]
        return JSONResponse({"razorpay_order_id": mock_id,
                             "amount": total, "key": RAZORPAY_KEY_ID, "mock": True})


# ── Cart API ──────────────────────────────────────────────────────────────

@app.post("/api/cart/add")
async def api_cart_add(request: Request, item: CartItemIn, db: AsyncSession = Depends(get_db)):
    sid    = get_session_id(request)
    result = await db.execute(select(Product).where(Product.id == item.product_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Product not found")
    cart = cart_store.setdefault(sid, [])
    for ex in cart:
        if ex["product_id"] == item.product_id:
            ex["quantity"] += item.quantity
            resp = JSONResponse({"message": "Updated", "count": len(cart)})
            set_cookie(resp, sid)
            return resp
    cart.append({"product_id": item.product_id, "quantity": item.quantity})
    resp = JSONResponse({"message": "Added", "count": len(cart)})
    set_cookie(resp, sid)
    return resp


@app.post("/api/cart/remove/{product_id}")
async def api_cart_remove(request: Request, product_id: str):
    sid = get_session_id(request)
    cart_store[sid] = [i for i in cart_store.get(sid, []) if i["product_id"] != product_id]
    return JSONResponse({"message": "Removed", "count": len(cart_store[sid])})


@app.post("/api/cart/update/{product_id}")
async def api_cart_update(request: Request, product_id: str, quantity: int = Form(...)):
    sid  = get_session_id(request)
    cart = cart_store.get(sid, [])
    for item in cart:
        if item["product_id"] == product_id:
            if quantity <= 0:
                cart_store[sid] = [i for i in cart if i["product_id"] != product_id]
            else:
                item["quantity"] = quantity
            break
    return JSONResponse({"message": "Updated"})


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "ShopKart is running!"}
