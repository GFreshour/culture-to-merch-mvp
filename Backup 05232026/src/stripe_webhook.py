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

print("🚀 Webhook server starting...")
print(f"🔑 Stripe key loaded: {'Yes' if stripe.api_key else 'No'}")
print(f"🔐 Webhook secret loaded: {'Yes' if endpoint_secret else 'No'}")

# =========================
# HELPERS
# =========================
def get_customer_email(customer_id):
    try:
        print(f"🔍 Fetching customer email for ID: {customer_id}")
        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get("email")
        print(f"📧 Found email: {email}")
        return email
    except Exception as e:
        print(f"❌ Error retrieving customer: {e}")
        return None


def now_utc():
    return str(datetime.now(timezone.utc))


# =========================
# WEBHOOK
# =========================
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    print("\n==================== NEW WEBHOOK ====================")

    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    print(f"📦 Payload size: {len(payload)} bytes")

    if not sig_header:
        print("🚫 Missing Stripe signature header")
        return jsonify(success=False), 400
    
    if len(payload) > 100000:  # ~100KB
        print("🚫 Payload too large")
        return jsonify(success=False), 400

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        print(f"❌ Webhook signature error: {e}")
        return jsonify(success=False), 400

    event_type = event['type']
    print(f"📩 EVENT TYPE: {event_type}")

    # =========================
    # 1. CHECKOUT COMPLETED (PRIMARY CREATE)
    # =========================
    if event_type == 'checkout.session.completed':
        session = event['data']['object']

        email = session.get("customer_details", {}).get("email")
        full_name = session.get("customer_details", {}).get("name")

        first_name = full_name.split(" ")[0] if full_name else None
        last_name = full_name.split(" ")[-1] if full_name else None

        print(f"✅ Checkout completed")
        print(f"   📧 Email: {email}")
        print(f"   👤 Name: {full_name}")

        if email:
            print("📤 Sending to Brevo: Tier 2 / Active")

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

            print("✅ Brevo update complete")

        else:
            print("⚠️ No email found in checkout session")

    # =========================
    # 2. INVOICE PAID (RENEWAL)
    # =========================
    elif event_type == 'invoice.paid':
        invoice = event['data']['object']
        customer_id = invoice.get("customer")

        print(f"💰 Invoice paid")
        print(f"   🆔 Customer ID: {customer_id}")

        email = get_customer_email(customer_id)

        if email:
            print(f"📤 Updating renewal for: {email}")

            update_user_tier(
                email=email,
                tier="Tier 2",
                pdf_access="Yes",
                sub_status="Active"
            )

            print("✅ Brevo renewal update complete")

        else:
            print("⚠️ No email found for invoice")

    # =========================
    # 3. SUBSCRIPTION CANCELLED
    # =========================
    elif event_type == 'customer.subscription.deleted':
        sub = event['data']['object']
        customer_id = sub.get("customer")

        print(f"⚠️ Subscription cancelled")
        print(f"   🆔 Customer ID: {customer_id}")

        email = get_customer_email(customer_id)

        if email:
            print(f"📤 Downgrading user: {email}")

            update_user_tier(
                email=email,
                tier="Tier 1",
                pdf_access="No",
                sub_status="Inactive"
            )

            print("✅ Brevo downgrade complete")

        else:
            print("⚠️ No email found for cancellation")

    else:
        print(f"ℹ️ Event ignored: {event_type}")

    print("==================== END WEBHOOK ====================\n")

    return jsonify(success=True)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4242)