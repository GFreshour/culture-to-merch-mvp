
from flask import Flask, request, jsonify
import stripe
import os
from datetime import datetime, timezone
from brevo_client import update_user_tier

app = Flask(__name__)

# =========================
# ENV VARIABLES (REQUIRED)
# =========================
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
stripe.api_key = os.getenv("STRIPE_API_KEY")

# =========================
# HELPERS
# =========================
def get_customer_email(customer_id):
    try:
        customer = stripe.Customer.retrieve(customer_id)
        return customer.get("email")
    except Exception as e:
        print(f"❌ Error retrieving customer: {e}")
        return None


def now_utc():
    return str(datetime.now(timezone.utc))


# =========================
# WEBHOOK
# =========================
@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        print(f"❌ Webhook signature error: {e}")
        return jsonify(success=False), 400

    event_type = event['type']
    print(f"\n📩 EVENT: {event_type}")

    # =========================
    # 1. CHECKOUT COMPLETED (PRIMARY CREATE)
    # =========================
    if event_type == 'checkout.session.completed':
        session = event['data']['object']

        email = session.get("customer_details", {}).get("email")
        first_name = session.get("customer_details", {}).get("name", "").split(" ")[0] if session.get("customer_details", {}).get("name") else None
        last_name = session.get("customer_details", {}).get("name", "").split(" ")[-1] if session.get("customer_details", {}).get("name") else None

        print(f"✅ Checkout completed → {email}")

        if email:
            update_user_tier(
                email=email,
                tier="Tier 2",
                first_name=first_name,
                last_name=last_name,
                created_at=now_utc(),
                plan_start=now_utc(),
                pdf_access="Yes",
                sub_status="Active"
            )

    # =========================
    # 2. INVOICE PAID (RENEWAL)
    # =========================
    elif event_type == 'invoice.paid':
        invoice = event['data']['object']
        email = get_customer_email(invoice.get("customer"))

        print(f"💰 Renewal payment → {email}")

        if email:
            update_user_tier(
                email=email,
                tier="Tier 2",
                pdf_access="Yes",
                sub_status="Active"
            )

    # =========================
    # 3. SUBSCRIPTION CANCELLED
    # =========================
    elif event_type == 'customer.subscription.deleted':
        sub = event['data']['object']
        email = get_customer_email(sub.get("customer"))

        print(f"⚠️ Subscription cancelled → {email}")

        if email:
            update_user_tier(
                email=email,
                tier="Tier 1",
                pdf_access="No",
                sub_status="Inactive"
            )

    else:
        print("ℹ️ Event ignored")

    return jsonify(success=True)


if __name__ == '__main__':
    app.run(port=4242)
