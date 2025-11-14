# Step-by-Step Deployment Guide

## Pre-Deployment Checklist

- [ ] Firebase credentials file (`firebase_credentials.json`) exists
- [ ] All environment variables are set in `.env`
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Tested locally with `test_webhook.py`
- [ ] GitHub repository created

---

## Part 1: Local Testing (Do This First!)

### Step 1: Install Dependencies

```bash
cd backend_py
pip install -r requirements.txt
```

### Step 2: Start the Server

```bash
uvicorn main:app --reload
```

Expected output:
```
✅ Firebase Admin SDK initialized
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Test Health Check

Open browser: `http://localhost:8000/health`

Should see:
```json
{"status": "healthy", "service": "notification-service"}
```

### Step 4: Test Notification Webhook

1. Get a user ID from your Supabase `kyc_profile` table that has an `fcm_token`
2. Edit `test_webhook.py` and replace `USER_ID_HERE` with the actual user ID
3. Run test:

```bash
python test_webhook.py
```

Expected output:
```
✅ Webhook test successful!
```

4. **Check your mobile device** - you should receive a push notification!

If everything works locally, proceed to deployment.

---

## Part 2: Railway Deployment

### Step 1: Prepare Firebase Credentials for Railway

Firebase credentials can't be committed to Git. We'll use base64 encoding:

**On Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("firebase_credentials.json")) | Set-Clipboard
```

**On Linux/Mac:**
```bash
base64 firebase_credentials.json | pbcopy  # or xclip on Linux
```

This copies the base64 string to your clipboard. **Save this somewhere secure!**

### Step 2: Push Code to GitHub

```bash
# If not already a git repo
git init

# Add files
git add .

# Commit
git commit -m "Initial notification backend setup"

# Create GitHub repo (or use existing)
# Then push
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 3: Create Railway Project

1. Go to https://railway.app
2. Click "Login with GitHub"
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository
6. Select the `backend_py` folder if prompted (or use "Root Directory" setting)

### Step 4: Configure Railway Environment Variables

In Railway Dashboard → Your Project → Variables:

Add these variables:

```
SUPABASE_URL=https://boyckkasuklyzybvngml.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJveWNra2FzdWtseXp5YnZuZ21sIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjI5MjMwNSwiZXhwIjoyMDcxODY4MzA1fQ.Jt7UOPi93sjx9-uV0Hj1Xp6dgulY8v3k72qXLNNWUlE
FIREBASE_CREDENTIALS_BASE64=<paste_your_base64_string_here>
```

**Important Notes:**
- Use your actual Supabase credentials
- Paste the entire base64 string for `FIREBASE_CREDENTIALS_BASE64`
- Don't add quotes around values in Railway

### Step 5: Configure Build Settings (if needed)

If Railway doesn't auto-detect:

1. Go to Settings → Deploy
2. Set **Root Directory**: `backend_py` (if your repo root is `geza_app`)
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 6: Deploy

Railway will automatically deploy. Watch the logs in the Dashboard.

Expected logs:
```
🔑 Decoding Firebase credentials from base64...
✅ Firebase credentials decoded successfully
✅ Firebase Admin SDK initialized
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 7: Get Your Webhook URL

1. In Railway Dashboard, click "Settings" → "Networking"
2. Click "Generate Domain"
3. Your webhook URL will be:
   ```
   https://your-service.up.railway.app/notify-user
   ```

4. Copy this URL - you'll need it for Supabase webhooks!

### Step 8: Test Deployed Service

Test health check:
```bash
curl https://your-service.up.railway.app/health
```

Should return:
```json
{"status":"healthy","service":"notification-service"}
```

---

## Part 3: Configure Supabase Webhooks

You need to create **3 webhooks** (one for each table).

### Webhook 1: Bookings/Service Requests

1. Go to Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **Database** → **Webhooks**
4. Click "**Enable Webhooks**" (if not already enabled)
5. Click "**Create a new hook**"

Configure:
- **Name**: `notify_on_new_booking`
- **Table**: `service_bookings`
- **Events**: ✅ Insert
- **Type**: HTTP Request
- **Method**: POST
- **URL**: `https://your-service.up.railway.app/notify-user`
- **HTTP Headers**:
  ```
  Content-Type: application/json
  ```
- Click "**Create webhook**"

### Webhook 2: Messages

Repeat the same process:
- **Name**: `notify_on_new_message`
- **Table**: `messages`
- **Events**: ✅ Insert
- **Method**: POST
- **URL**: `https://gezabacked.onrender.com/notify-user`
- **HTTP Headers**: `Content-Type: application/json`

### Webhook 3: Orders/Sales

Repeat again:
- **Name**: `notify_on_new_order`
- **Table**: `sale_orders`
- **Events**: ✅ Insert
- **Method**: POST
- **URL**: `https://your-service.up.railway.app/notify-user`
- **HTTP Headers**: `Content-Type: application/json`

---

## Part 4: End-to-End Testing

### Test 1: Create a Booking

1. Use your Flutter app to create a new booking/service request
2. Check Railway logs for:
   ```
   📥 Webhook received for table: service_bookings
   📤 Sending notification to user: <user_id>
   Sent 1 messages successfully.
   ```
3. **Check the seller's mobile device** for notification!

### Test 2: Send a Message

1. Send a chat message in your Flutter app
2. Check Railway logs
3. **Check the recipient's mobile device** for notification!

### Test 3: Create an Order

1. Create a new order in your Flutter app
2. Check Railway logs
3. **Check the seller's mobile device** for notification!

---

## Troubleshooting

### "No FCM token found for user"

**Problem**: User hasn't logged in or token wasn't saved.

**Solution**:
1. Make sure user has logged into the Flutter app
2. Check Supabase `kyc_profile` table - look for `fcm_token` column
3. Token should be a long string like: `cXy1z...`
4. If empty, logout and login again in the app

### "Firebase Admin SDK Error"

**Problem**: Firebase credentials are incorrect or not loaded.

**Solution**:
1. Check Railway logs for "✅ Firebase credentials decoded successfully"
2. Verify `FIREBASE_CREDENTIALS_BASE64` is set correctly
3. Re-generate base64 string and update in Railway
4. Redeploy

### Webhook Not Firing

**Problem**: Supabase isn't calling your Railway endpoint.

**Solution**:
1. Check webhook is enabled in Supabase
2. Verify URL is correct (no trailing slash)
3. Check Supabase webhook logs:
   - Go to Database → Webhooks
   - Click on your webhook
   - View "Recent Deliveries"
4. Look for HTTP errors

### Railway Deployment Failed

**Problem**: Build or deploy errors.

**Solution**:
1. Check Railway logs for specific error
2. Common issues:
   - Wrong root directory
   - Missing `requirements.txt`
   - Python version mismatch
3. Try manual commands locally first

### Notification Not Received on Mobile

**Problem**: Backend sends notification but mobile doesn't show it.

**Checklist**:
1. ✅ App has notification permissions enabled
2. ✅ FCM token is saved in database
3. ✅ Token matches the device
4. ✅ App is connected to internet
5. ✅ Firebase project is correct
6. ✅ Check Railway logs show "Sent 1 messages successfully"

---

## Monitoring & Maintenance

### View Railway Logs

**Live logs:**
```bash
railway logs --follow
```

**In Dashboard:**
- Go to your project → Deployments → Click latest deployment → Logs

### Update Code

```bash
git add .
git commit -m "Update notification logic"
git push
```

Railway will auto-deploy on push!

### Monitor Webhook Health

Check Supabase webhook status:
1. Database → Webhooks
2. Each webhook shows:
   - Total deliveries
   - Success rate
   - Recent deliveries

### Update Column Names

If your table columns are different, edit `main.py`:

```python
# Example: Change 'seller_id' to 'vendor_id'
recipient_user_id = new_record.get('vendor_id') or new_record.get('seller_id')
```

Then commit and push to update.

---

## Success Checklist

After completing all steps:

- [ ] Local testing works
- [ ] Railway deployed successfully
- [ ] Health check endpoint works
- [ ] 3 Supabase webhooks created
- [ ] Booking notification works
- [ ] Message notification works
- [ ] Order notification works
- [ ] Mobile app receives notifications

---

## Need Help?

1. Check Railway logs first
2. Check Supabase webhook delivery logs
3. Verify FCM tokens in database
4. Test locally with `test_webhook.py`
5. Compare your setup with this guide

## Quick Reference

**Local Server:**
```bash
uvicorn main:app --reload
```

**Test Webhook:**
```bash
python test_webhook.py
```

**Railway Logs:**
```bash
railway logs
```

**Health Check:**
```
http://localhost:8000/health  (local)
https://your-service.up.railway.app/health  (production)
```

**Webhook Endpoint:**
```
http://localhost:8000/notify-user  (local)
https://your-service.up.railway.app/notify-user  (production)
```
