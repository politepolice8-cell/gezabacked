import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, messaging
from supabase import create_client, Client
from fastapi import FastAPI # If using FastAPI

from fastapi import Request
import json
import asyncio
import base64

# --- LOAD ENVIRONMENT VARIABLES ---
# This line must be the first thing you call
load_dotenv()

# --- 1. INITIALIZE SERVICES ---

# 1a. Handle Firebase credentials (support both file and base64)
firebase_creds_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
if firebase_creds_base64:
    # Decode base64 credentials (for Railway deployment)
    print("🔑 Decoding Firebase credentials from base64...")
    try:
        creds_json = base64.b64decode(firebase_creds_base64).decode('utf-8')
        with open("firebase_credentials.json", "w") as f:
            f.write(creds_json)
        print("✅ Firebase credentials decoded successfully")
    except Exception as e:
        print(f"❌ Error decoding Firebase credentials: {e}")

# 1b. Initialize Firebase Admin SDK
try:
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized")
except ValueError:
    print("⚠️  Firebase Admin SDK already initialized")
    pass # Already initialized
except Exception as e:
    print(f"❌ Error initializing Firebase Admin SDK: {e}")
    raise

# 1b. Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# --- HEALTH CHECK ENDPOINT ---
@app.get("/")
@app.head("/")
@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint for Render/Railway"""
    return {"status": "healthy", "service": "notification-service"}

# --- 2. FCM SENDING FUNCTION ---

def send_fcm_notification(user_id: str, title: str, body: str, custom_data: dict = None):
    """
    Fetches the FCM token for a user from kyc_profile table and sends the FCM message.
    """
    # 2a. Fetch FCM Token from kyc_profile table
    try:
        response = supabase.table('kyc_profile').select('push_token').eq('id', user_id).execute()

        if not response.data or len(response.data) == 0:
            print(f"No profile found for user_id: {user_id}")
            return

        push_token = response.data[0].get('push_token')

        if not push_token:
            print(f"No FCM token found for user_id: {user_id}")
            return

        tokens = [push_token]

    except Exception as e:
        print(f"Error fetching FCM token: {e}")
        return

    if not tokens:
        print(f"No valid tokens found for user_id: {user_id}")
        return

    # 2b. Construct the Message Payload for each token
    # Convert custom_data values to strings (FCM requirement)
    data_payload = {}
    if custom_data:
        data_payload = {k: str(v) for k, v in custom_data.items()}

    # 2c. Send the Message and Handle Errors
    success_count = 0
    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data_payload,
                token=token,
            )

            response = messaging.send(message)
            print(f"✅ Successfully sent message: {response}")
            success_count += 1

        except messaging.UnregisteredError:
            # Token is invalid (e.g., app uninstalled) - Clean up your database!
            print(f"❌ Token UNREGISTERED: {token[:20]}... Clearing from DB...")
            try:
                supabase.table('kyc_profile').update({'push_token': None}).eq('push_token', token).execute()
            except Exception as db_error:
                print(f"⚠️  Error clearing token from DB: {db_error}")

        except firebase_admin.exceptions.FirebaseError as e:
            print(f"❌ Firebase Error for token {token[:20]}...: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    print(f"📊 Sent {success_count}/{len(tokens)} messages successfully.")

# Example of calling the function:
# send_fcm_notification(
#     user_id="user-123", 
#     title="New Notification!", 
#     body="A user has engaged with your content.",
#     custom_data={'page': 'profile', 'source_id': '456'}
# )

@app.post("/notify-user")
async def handle_supabase_webhook(request: Request):
    """
    Handles the incoming webhook POST request from Supabase.
    Supports: bookings (service_bookings), messages (messages), orders (sale_orders)
    """
    try:
        # 1. Read the JSON payload sent by Supabase
        payload = await request.json()

        # 2. Extract the new/old record data and table name
        new_record = payload.get('record', {})
        old_record = payload.get('old_record') or {}
        table_name = payload.get('table', '')

        print(f"📥 Webhook received for table: {table_name}")
        print(f"📋 Record data: {new_record}")

        # 3. Determine notification details based on table type
        recipient_user_id = None
        notification_title = "New Activity"
        notification_body = "You have a new update"
        custom_data = {'table': table_name}

        # Handle different table types
        if table_name == 'service_booking':
            # IMPORTANT: For broadcasts/quests, the Flutter app handles notifications to ALL stylists
            # via sendBroadcastNotificationToAllStylists() in sales_controller.dart
            # This webhook should ONLY handle direct bookings (category='direct_booking')
            if new_record.get('category') == 'broadcast':
                print("ℹ️ Broadcast detected - Flutter app handles stylist notifications, skipping webhook")
                return {
                    "status": "skipped",
                    "message": "Broadcast notifications handled by Flutter app"
                }

            # For direct bookings - notify the service provider
            recipient_user_id = (
                new_record.get('service_provider_id')
                or new_record.get('provider_id')
                or new_record.get('seller_id')
                or new_record.get('vendor_id')
            )

            if not recipient_user_id:
                print("⚠️ No recipient ID found in service_booking payload. Keys:", list(new_record.keys()))
                print("⚠️ Record payload:", new_record)
                return {"status": "error", "message": "Recipient ID not found in booking payload"}

            booking_id = new_record.get('id')
            notification_title = "New Booking Request"
            notification_body = "You have a new service booking request"
            custom_data = {
                'type': 'new_booking',
                'booking_id': booking_id,
                'table': table_name
            }

        elif table_name == 'chats':
            # For chat messages - notify the recipient
            recipient_user_id = (
                new_record.get('userid')
                or new_record.get('user_id')
                or new_record.get('receiver_id')
                or new_record.get('receiverId')
                or new_record.get('userId')
            )

            sender_id = (
                new_record.get('isme')
                or new_record.get('sender_id')
                or new_record.get('senderId')
            )

            message_content = (
                new_record.get('text')
                or new_record.get('content')
                or 'sent you a message'
            )

            chat_id = new_record.get('chatid') or new_record.get('chat_id')

            if not recipient_user_id:
                print("⚠️ Chat webhook missing recipient ID. Available keys:", list(new_record.keys()))
                print("⚠️ Record payload:", new_record)
                return {"status": "error", "message": "Recipient ID not found in chat payload"}

            # Optionally fetch sender's name from kyc_profile
            sender_name = 'Someone'
            if sender_id:
                try:
                    sender_profile = supabase.table('kyc_profile').select('username').eq('id', sender_id).execute()
                    if sender_profile.data and len(sender_profile.data) > 0:
                        sender_name = sender_profile.data[0].get('username', sender_name)
                except Exception as lookup_error:
                    print(f"⚠️ Error looking up sender name: {lookup_error}")

            notification_title = f"New message from {sender_name}"
            notification_body = message_content[:100]  # Truncate long messages
            custom_data = {
                'type': 'new_message',
                'chat_id': chat_id,
                'message_id': new_record.get('id'),
                'sender_id': sender_id,
                'table': table_name
            }

        elif table_name == 'sale_order':
            # For orders - notify the seller
            recipient_user_id = new_record.get('seller_id') or new_record.get('vendor_id')
            order_id = new_record.get('id')
            notification_title = "New Order"
            notification_body = f"You have a new order"
            custom_data = {
                'type': 'new_order',
                'order_id': order_id,
                'table': table_name
            }

        elif table_name == 'product':
            new_tags = set(new_record.get('tagged_profiles_ids') or [])

            # Check if we have old_record to compare, otherwise treat all tags as new (for INSERT events)
            if old_record:
                old_tags = set(old_record.get('tagged_profiles_ids') or [])
                newly_tagged = [pid for pid in new_tags if pid not in old_tags]
                print(f"ℹ️ Product UPDATE: old tags={len(old_tags)}, new tags={len(new_tags)}, newly_tagged={len(newly_tagged)}")
            else:
                # No old_record means this might be an INSERT or webhook doesn't send old_record
                # Only send notifications if tags exist (not empty)
                newly_tagged = list(new_tags) if new_tags else []
                print(f"ℹ️ Product event (no old_record): tags={len(new_tags)}, will notify={len(newly_tagged)}")

            if not newly_tagged:
                print("ℹ️ No new profiles to notify for product tags.")
                return {"status": "ignored", "message": "No new profiles tagged"}

            product_name = new_record.get('product_name', 'a product')
            tagged_by = new_record.get('business_name') or new_record.get('created_by_name') or "Someone"
            notification_title = "You've been tagged!"
            notification_body = f"{tagged_by} tagged you to {product_name}"
            custom_data = {
                'type': 'product_tag',
                'product_id': new_record.get('id'),
                'product_name': product_name,
                'tagged_by': tagged_by,
                'table': table_name
            }

            sent_count = 0
            for profile_id in newly_tagged:
                print(f"📤 Sending tag notification to user: {profile_id}")
                send_fcm_notification(
                    user_id=profile_id,
                    title=notification_title,
                    body=notification_body,
                    custom_data=custom_data
                )
                sent_count += 1

            return {"status": "success", "message": f"Tag notifications sent to {sent_count} users"}

        elif table_name == 'kyc_profile':
            # New user registration - send a welcome notification
            if payload.get('type') != 'INSERT':
                return {"status": "ignored", "message": "Only INSERT events trigger welcome notifications"}

            recipient_user_id = new_record.get('id')
            if not recipient_user_id:
                print("⚠️ No user ID found for kyc_profile insert.")
                return {"status": "error", "message": "User ID missing in kyc_profile payload"}

            user_name = new_record.get('username') or new_record.get('full_name') or "there"
            notification_title = "Welcome to StyleFinder!"
            notification_body = f"Hi {user_name}, thanks for joining us. You're all set."
            custom_data = {
                'type': 'welcome',
                'table': table_name
            }

        else:
            print(f"⚠️ Unknown table type: {table_name}")
            return {"status": "ignored", "message": f"Table '{table_name}' not configured for notifications"}

        # 4. Validate recipient ID
        if not recipient_user_id:
            print(f"⚠️ No recipient ID found in record for table: {table_name}")
            return {"status": "error", "message": "Recipient ID not found in payload"}

        # 5. Send the FCM notification
        print(f"📤 Sending notification to user: {recipient_user_id}")
        send_fcm_notification(
            user_id=recipient_user_id,
            title=notification_title,
            body=notification_body,
            custom_data=custom_data
        )

        return {"status": "success", "message": "Notification sent successfully"}

    except Exception as e:
        # Log the error and return a non-500 response (Supabase stops sending webhooks on repeated failures)
        print(f"❌ WEBHOOK ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failure", "message": f"Processing error: {str(e)}"}