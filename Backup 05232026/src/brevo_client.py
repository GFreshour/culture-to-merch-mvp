import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

BREVO_LIST_ID = int(os.getenv("BREVO_LIST_ID", "12"))
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

def update_user_tier(
    email: str,
    tier: str = "Tier 1",
    first_name: str = None,
    last_name: str = None,
    created_at: str = None,
    plan_start: str = None,
    pdf_access: str = None,
    sub_status: str = "Inactive",
    list_id: int = None,
    **kwargs  # allows extra attributes in the future
):
    """
    Adds or updates a Brevo contact with tier, subscription status, and custom attributes.
    """

    if not list_id:
        list_id = BREVO_LIST_ID

    print(f"🔹 Attempting Brevo update")
    print(f"Email: {email}")
    print(f"Tier: {tier}")
    print(f"List ID: {list_id}")
    print(f"Using API Key: {'Set' if BREVO_API_KEY else 'Not set'}")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = BREVO_API_KEY
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    contacts_api = sib_api_v3_sdk.ContactsApi(api_client)

    # Use current UTC time if timestamps not provided
    now_iso = created_at or plan_start or None
    if not now_iso:
        from datetime import datetime
        now_iso = datetime.utcnow().isoformat()

    attributes = {
        "TIER_LEVEL": tier,
        "SUB_STATUS": sub_status,
        "CREATED_AT": created_at or now_iso,
        "PLAN_START": plan_start or now_iso,
        "PDF_ACCESS": pdf_access or ("Yes" if tier.lower() == "tier 2" else "No"),
    }

    # Add optional fields if provided
    if first_name:
        attributes["FIRST_NAME"] = first_name
    if last_name:
        attributes["LAST_NAME"] = last_name

    # Include any additional attributes passed via kwargs
    attributes.update(kwargs)

    contact_data = sib_api_v3_sdk.CreateContact(
        email=email,
        attributes=attributes,
        list_ids=[list_id],
        update_enabled=True
    )

    try:
        response = contacts_api.create_contact(contact_data)
        print(f"✅ Brevo contact updated/added: {email}")
        print(f"Response: {response}")
    except ApiException as e:
        print(f"❌ Failed to update/add Brevo contact: {e}")
        if e.body:
            print(f"Response body: {e.body}")