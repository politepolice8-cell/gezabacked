# Render Deployment Fix

## Issue
Your service is running on `127.0.0.1:8000` but Render needs it on `0.0.0.0:$PORT` (port 10000 by default).

Also, the `--reload` flag should NOT be used in production.

## Solution

### Fix 1: Update Start Command in Render Dashboard

1. Go to https://dashboard.render.com
2. Select your service "gezabacked"
3. Go to **Settings** tab
4. Scroll to **Build & Deploy** section
5. Change **Start Command** from:
   ```
   uvicorn main:app --reload
   ```
   To:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
6. Click "**Save Changes**"
7. Render will automatically redeploy

### Fix 2: Add HEAD Method Support

The error shows `HEAD / HTTP/1.1" 405 Method Not Allowed`. Let me update the health endpoint to support HEAD requests.

### Fix 3: Verify Environment Variables

Make sure these are set in Render Dashboard → Settings → Environment:

```
SUPABASE_URL=https://boyckkasuklyzybvngml.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJveWNra2FzdWtseXp5YnZuZ21sIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjI5MjMwNSwiZXhwIjoyMDcxODY4MzA1fQ.Jt7UOPi93sjx9-uV0Hj1Xp6dgulY8v3k72qXLNNWUlE
FIREBASE_CREDENTIALS_BASE64=<your_base64_string>
```

### Fix 4: After Deployment

Once redeployed, test your endpoints:

**Health Check:**
```bash
curl https://gezabacked.onrender.com/health
```

Expected response:
```json
{"status":"healthy","service":"notification-service"}
```

**Test Webhook:**
Update your `test_webhook.py` with the Render URL and test:
```python
test_webhook("booking", base_url="https://gezabacked.onrender.com")
```

## Your Webhook URL for Supabase

After the fix is applied, your webhook URL will be:
```
https://gezabacked.onrender.com/notify-user
```

Use this URL in your Supabase webhook configuration!

## Monitoring

View logs in real-time:
- Go to Render Dashboard → Your Service → Logs

You should see:
```
✅ Firebase Admin SDK initialized
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Important Notes

1. **Render Free Tier**: Services spin down after 15 minutes of inactivity
   - First request after spin-down takes ~30-60 seconds
   - This may cause webhook delays

2. **Keep-Alive**: Consider upgrading to paid tier or using a keep-alive service

3. **Firebase Credentials**: Make sure `FIREBASE_CREDENTIALS_BASE64` is properly set

## Troubleshooting

**If still seeing "No open ports detected":**
1. Check Start Command is correct (no `--reload`)
2. Ensure `--host 0.0.0.0` is specified
3. Verify `$PORT` variable is used (Render provides this)

**If Firebase errors:**
1. Check `FIREBASE_CREDENTIALS_BASE64` is set
2. Verify base64 encoding is correct
3. Check Render logs for "✅ Firebase credentials decoded successfully"
