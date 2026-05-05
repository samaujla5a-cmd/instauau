# 🌿 Rap Automation — Instagram Only Setup Guide

## What This Does
- 3 Instagram channels running 24/7 automatically
- 30 posts per day (10 per channel)
- Channel 1: Rap music reels
- Channel 2: Brainrot viral content
- Channel 3: AI lifestyle model content
- Hosted FREE on Railway

---

## STEP 1 — Get Your Anthropic API Key (5 minutes)
1. Go to https://console.anthropic.com
2. Sign up / Log in
3. Click "API Keys" → "Create Key"
4. Copy the key (starts with sk-ant-)
5. Save it — you will need it in Step 4

---

## STEP 2 — Upload Code to GitHub (5 minutes)
1. Go to https://github.com and sign up if needed
2. Click "New Repository"
3. Name it: rap-automation
4. Set to Private
5. Click "Create Repository"
6. Upload ALL files from this zip to that repo
   - Click "Add file" → "Upload files"
   - Drag ALL files/folders into the box
   - Click "Commit changes"

---

## STEP 3 — Deploy to Railway (5 minutes)
1. Go to https://railway.app and sign up (free)
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub account
4. Select your rap-automation repo
5. Railway will start building automatically

---

## STEP 4 — Add Environment Variables (3 minutes)
In Railway → your project → "Variables" tab, add these:

REQUIRED:
  ANTHROPIC_API_KEY     = sk-ant-your-key-here
  MUSIC_MODE            = gtts_only
  TTS_MODE              = edge_tts

YOUR 3 INSTAGRAM ACCOUNTS:
  RAP_IG_USERNAME       = your_rap_account
  RAP_IG_PASSWORD       = your_rap_password
  BRAINROT_IG_USERNAME  = your_brainrot_account
  BRAINROT_IG_PASSWORD  = your_brainrot_password
  MODEL_IG_USERNAME     = your_model_account
  MODEL_IG_PASSWORD     = your_model_password

Click "Deploy" after adding variables.

---

## STEP 5 — Get Your Dashboard URL (1 minute)
1. In Railway → your service → Settings → Networking
2. Click "Generate Domain"
3. You get a URL like: yourapp.up.railway.app
4. Open it — you will see the live dashboard

---

## STEP 6 — Verify It Is Working
Your dashboard shows:
✅ Green badges = accounts connected
✅ Logs streaming = bot is running
✅ First posts appear at next scheduled time

Post schedule (UTC times):
- Rap:      00:00, 02:30, 05:00, 07:00, 09:00, 11:00, 13:00, 15:00, 17:00, 19:00
- Brainrot: 00:20, 02:50, 05:20, 07:20, 09:20, 11:20, 13:20, 15:20, 17:20, 19:20
- Model:    00:40, 03:10, 05:40, 07:40, 09:40, 11:40, 13:40, 15:40, 17:40, 19:40

---

## OPTIONAL — Better Music with Suno
1. Go to suno.ai and create a free account
2. Log in → Press F12 → Network tab
3. Click any button on the page
4. Find any request → Headers → copy the Cookie: value
5. Add to Railway variables:
   MUSIC_MODE = suno_cookie
   SUNO_COOKIE = (paste your cookie here)

---

## TROUBLESHOOTING

Problem: Instagram login fails
Fix: Make sure accounts are at least 3 days old
Fix: Log into Instagram from your phone first, then retry

Problem: No videos being created
Fix: Check Railway logs for errors
Fix: Make sure ANTHROPIC_API_KEY is set correctly

Problem: Dashboard not loading
Fix: Make sure you generated the domain in Railway networking settings

---

## COSTS
- Railway: FREE (500 hours/month free tier)
- Anthropic API: FREE tier available, very cheap after
- Instagram: FREE
- Music (gtts_only mode): COMPLETELY FREE
- Total monthly cost: $0
