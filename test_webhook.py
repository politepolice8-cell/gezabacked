"""
Test script for webhook endpoint
Run this to test the notification webhook locally
"""
import requests
import json

# Test payloads for different table types
test_payloads = {
    "booking": {
        "table": "service_booking",
        "record": {
            "id": "test-booking-123",
            "seller_id": "917892d9-908e-40c5-91c7-4c6767a8741f",  # Replace with actual user ID
            "buyer_id": "buyer-456",
            "service_name": "Test Service",
            "created_at": "2025-01-13T10:00:00Z"
        }
    },
    "message": {
        "table": "messages",
        "record": {
            "id": "test-msg-123",
            "receiver_id": "USER_ID_HERE",  # Replace with actual user ID
            "sender_name": "John Doe",
            "content": "Hey, this is a test message!",
            "chat_id": "chat-789",
            "created_at": "2025-01-13T10:00:00Z"
        }
    },
    "order": {
        "table": "sale_orders",
        "record": {
            "id": "test-order-123",
            "seller_id": "USER_ID_HERE",  # Replace with actual user ID
            "buyer_id": "buyer-456",
            "total_amount": 99.99,
            "created_at": "2025-01-13T10:00:00Z"
        }
    }
}

def test_webhook(payload_type="booking", base_url="http://localhost:8000"):
    """
    Test the webhook endpoint

    Args:
        payload_type: "booking", "message", or "order"
        base_url: Base URL of your API (default: http://localhost:8000)
    """
    if payload_type not in test_payloads:
        print(f"❌ Invalid payload type. Choose from: {list(test_payloads.keys())}")
        return

    payload = test_payloads[payload_type]

    print(f"\n🧪 Testing {payload_type} notification...")
    print(f"📤 Sending webhook to: {base_url}/notify-user")
    print(f"📋 Payload:\n{json.dumps(payload, indent=2)}\n")

    try:
        response = requests.post(
            f"{base_url}/notify-user",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        print(f"📥 Response Status: {response.status_code}")
        print(f"📋 Response Body:\n{json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("\n✅ Webhook test successful!")
        else:
            print("\n⚠️  Webhook returned non-200 status")

    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server. Make sure it's running!")
        print("   Run: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔔 Notification Webhook Tester")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Replace 'USER_ID_HERE' with a real user ID")
    print("              from your kyc_profile table that has an FCM token!\n")

    # Test all three types
    print("\nStarting tests...\n")

    # Uncomment the test you want to run:
    test_webhook("booking")
    # test_webhook("message")
    # test_webhook("order")

    print("\n" + "=" * 60)
