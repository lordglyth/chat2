from __future__ import annotations
import time
from .config import settings
from . import db


def create_checkout(email: str | None=None):
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise RuntimeError("Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID.")
    import stripe
    stripe.api_key=settings.stripe_secret_key
    kwargs={
      "mode":"subscription",
      "line_items":[{"price":settings.stripe_price_id,"quantity":1}],
      "success_url":settings.public_base_url.rstrip("/")+"/?subscribed=1",
      "cancel_url":settings.public_base_url.rstrip("/")+"/?subscribed=0",
      "allow_promotion_codes":True,
    }
    if email: kwargs["customer_email"]=email
    session=stripe.checkout.Session.create(**kwargs)
    return {"id":session.id,"url":session.url}


def handle_event(event):
    et=event.get("type","")
    obj=event.get("data",{}).get("object",{})
    if et=="checkout.session.completed":
        email=(obj.get("customer_details") or {}).get("email") or obj.get("customer_email")
        customer=str(obj.get("customer") or "")
        with db.connect() as con:
            existing=con.execute("SELECT id FROM subscribers WHERE stripe_customer_id=?",(customer,)).fetchone() if customer else None
            if existing:
                con.execute("UPDATE subscribers SET email=?,active=1 WHERE id=?",(email,existing["id"]))
            else:
                con.execute("INSERT INTO subscribers VALUES(?,?,?,?,?)",(db.uid(),email,customer,1,time.time()))
    elif et in ("customer.subscription.deleted","customer.subscription.paused"):
        customer=str(obj.get("customer") or "")
        if customer:
            with db.connect() as con: con.execute("UPDATE subscribers SET active=0 WHERE stripe_customer_id=?",(customer,))
    elif et in ("customer.subscription.updated","invoice.paid"):
        customer=str(obj.get("customer") or "")
        if customer:
            with db.connect() as con: con.execute("UPDATE subscribers SET active=1 WHERE stripe_customer_id=?",(customer,))
    db.log_event("stripe",{"type":et})
