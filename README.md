# Push Notification Backend Service

FastAPI backend service for handling push notifications via Firebase Cloud Messaging (FCM).

## Features

- Receives webhook calls from Supabase
- Sends push notifications via Firebase Cloud Messaging
- Supports multiple notification types:
  - **Bookings/Service Requests** (`service_bookings` table)
  - **Chat Messages** (`messages` table)
  - **Orders/Sales** (`sale_orders` table)
- Automatic invalid token cleanup
- Health check endpoint

## Prerequisites

- Python 3.9+
- Firebase project with Cloud Messaging enabled
- Supabase project
- Railway account (for deployment)

## Setup

### 1. Environment Variables

Create a `.env` file with the following:

```env
SUPABASE_KEY=your_supabase_service_role_key
SUPABASE_URL=https://your-project.supabase.co
FIREBASE_CREDENTIALS_PATH=firebase_credentials.json
```

### 2. Firebase Credentials

1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate New Private Key"
3. Save the JSON file as `firebase_credentials.json` in the `backend_py` folder
4. **IMPORTANT**: Never commit this file to git!

### 3. Install Dependencies

```bash
cd backend_py
pip install -r requirements.txt
```

## Local Testing

### Start the Server

```bash
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

### Test the Webhook

1. Edit `test_webhook.py` and replace `USER_ID_HERE` with a real user ID from your database
2. Run the test:

```bash
python test_webhook.py
```

### Health Check

Visit `http://localhost:8000/health` to verify the service is running.

## Database Schema Requirements

### kyc_profile Table

Your `kyc_profile` table must have:
- `id` column (user ID)
- `fcm_token` column (TEXT, nullable)

### Trigger Tables

Configure these tables based on your needs:

#### service_bookings
- `id` - booking ID
- `seller_id` or `provider_id` - user to notify
- Other fields as needed

#### messages
- `id` - message ID
- `receiver_id` or `recipient_id` - user to notify
- `sender_name` - name of sender
- `content` - message text
- `chat_id` - chat identifier

#### sale_orders
- `id` - order ID
- `seller_id` or `vendor_id` - user to notify
- Other fields as needed

## Railway Deployment

### Step 1: Push Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Add notification backend"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### Step 2: Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect the configuration

### Step 3: Add Environment Variables

In Railway Dashboard → Variables, add:

```
SUPABASE_KEY=your_supabase_service_role_key
SUPABASE_URL=https://your-project.supabase.co
FIREBASE_CREDENTIALS_PATH=firebase_credentials.json
```

### Step 4: Upload Firebase Credentials

Since `firebase_credentials.json` is gitignored, you need to add it manually:

**Option A: Use Railway CLI**
```bash
railway login
railway link
railway up
# Manually copy firebase_credentials.json to the deployment
```

**Option B: Base64 Encode** (Recommended)
1. Convert your credentials to base64:
   ```bash
   # On Linux/Mac
   base64 firebase_credentials.json

   # On Windows (PowerShell)
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("firebase_credentials.json"))
   ```

2. Add to Railway as environment variable:
   ```
   FIREBASE_CREDENTIALS_BASE64=<your_base64_string>
   ```

3. Update `main.py` to decode:
   ```python
   import base64

   # Add after load_dotenv()
   firebase_creds_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
   if firebase_creds_base64:
       with open("firebase_credentials.json", "w") as f:
           f.write(base64.b64decode(firebase_creds_base64).decode())
   ```

### Step 5: Get Webhook URL

After deployment, Railway will provide a URL like:
```
https://your-service.up.railway.app
```

Your webhook endpoint will be:
```
https://your-service.up.railway.app/notify-user
```

## Supabase Webhook Configuration

### For Each Table (service_bookings, messages, sale_orders):

1. Go to Supabase Dashboard → Database → Webhooks
2. Click "Create a new hook"
3. Configure:
   - **Name**: `notify_user_on_new_booking` (or similar)
   - **Table**: Select the appropriate table
   - **Events**: Check "Insert"
   - **Type**: HTTP Request
   - **Method**: POST
   - **URL**: `https://your-service.up.railway.app/notify-user`
   - **HTTP Headers**:
     ```
     Content-Type: application/json
     ```

4. Click "Create webhook"

### Test Webhook from Supabase

After creating the webhook:
1. Insert a test record into the table
2. Check Railway logs to see if the webhook was received
3. Check your mobile device for the notification

## Monitoring & Debugging

### View Railway Logs

```bash
railway logs
```

Or view in Railway Dashboard → Deployments → Logs

### Common Issues

**"No FCM token found for user"**
- User hasn't logged in to the mobile app
- Token upload failed during app initialization
- Check `kyc_profile.fcm_token` column

**"Firebase Admin SDK Error"**
- Check Firebase credentials are correct
- Verify `firebase_credentials.json` is present
- Check Firebase project has FCM enabled

**"Recipient ID not found"**
- Column name mismatch (e.g., `seller_id` vs `provider_id`)
- Update the column names in `main.py` webhook handler

**Webhook not firing**
- Verify webhook is enabled in Supabase
- Check webhook URL is correct
- View webhook logs in Supabase Dashboard

## API Endpoints

### GET /
### GET /health
Health check endpoint
```json
{
  "status": "healthy",
  "service": "notification-service"
}
```

### POST /notify-user
Webhook endpoint for Supabase

**Request Body:**
```json
{
  "table": "service_bookings",
  "record": {
    "id": "booking-123",
    "seller_id": "user-456",
    ...
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Notification sent successfully"
}
```

## Security Notes

1. **Never commit** `firebase_credentials.json` or `.env` files
2. Use Supabase **service_role** key (has RLS bypass)
3. Consider adding webhook authentication (shared secret)
4. Enable HTTPS only in production

## Troubleshooting

### Local Development

1. Check all environment variables are set
2. Verify `firebase_credentials.json` exists
3. Confirm Supabase connection works
4. Use `test_webhook.py` to test manually

### Production (Railway)

1. Check Railway logs for errors
2. Verify all environment variables are set
3. Test health endpoint: `https://your-service.up.railway.app/health`
4. Check Supabase webhook logs

## Column Name Mapping

If your database uses different column names, update `main.py`:

```python
# Example: If your bookings table uses 'vendor_id' instead of 'seller_id'
recipient_user_id = new_record.get('vendor_id') or new_record.get('seller_id')
```

## Support

For issues:
1. Check Railway logs
2. Check Supabase webhook logs
3. Verify FCM tokens in database
4. Test locally with `test_webhook.py`
