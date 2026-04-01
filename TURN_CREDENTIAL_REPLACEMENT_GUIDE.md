# TURN Credential Replacement Guide

**When:** After initial testing if you need production-grade reliability  
**Why:** Shared public credentials can become rate-limited  
**Time:** 10-15 minutes including redeploy  

---

## Overview: Three Options

| Provider | Setup Time | Cost | Reliability | Scale |
|----------|-----------|------|-------------|-------|
| **Metered.ca** | 5 min | $4.99-49/mo | ⭐⭐⭐⭐ | Medium |
| **Twilio** | 10 min | $0.04-0.15/call | ⭐⭐⭐⭐⭐ | High |
| **Self-Hosted Coturn** | 30+ min | $5-20/mo (VPS) | ⭐⭐⭐ | Variable |

---

## Option 1: Metered.ca (Recommended for Most Users)

### Step 1: Create Account
1. Go to https://www.metered.ca/
2. Click "Sign Up"
3. Enter email, password
4. Verify email

### Step 2: Get Credentials
1. Log in to dashboard
2. Go to **API Keys** (left menu)
3. Create new API key
4. Copy the key (you'll use this as username + password)

**Example:**
```
API Key: abc123def456ghi789
```

### Step 3: Find Server Endpoints
1. Go to **TURN Servers** (left menu)
2. Select your region (pick closest to your users):
   - **Europe:** `turn.metered.ca` 
   - **US East:** `turn-us-east.metered.ca`
   - **US West:** `turn-us-west.metered.ca`
   - **Asia:** `turn-asia.metered.ca`

### Step 4: Update render.yaml

**Old:**
```yaml
- key: WEBRTC_ICE_SERVERS_JSON
  value: '[{"urls":"turn:openrelay.metered.ca:80",...
```

**New (Metered.ca):**
```yaml
- key: WEBRTC_ICE_SERVERS_JSON
  value: '[{"urls":["stun:stun.l.google.com:19302","stun:stun1.l.google.com:19302"]},{"urls":"turn:turn.metered.ca:80","username":"abc123def456ghi789","credential":"abc123def456ghi789"},{"urls":"turn:turn.metered.ca:80?transport=tcp","username":"abc123def456ghi789","credential":"abc123def456ghi789"},{"urls":"turn:turn.metered.ca:443","username":"abc123def456ghi789","credential":"abc123def456ghi789"},{"urls":"turn:turn.metered.ca:443?transport=tcp","username":"abc123def456ghi789","credential":"abc123def456ghi789"},{"urls":"turns:turn.metered.ca:443?transport=tcp","username":"abc123def456ghi789","credential":"abc123def456ghi789"}]'
```

**Replace:**
- `abc123def456ghi789` → Your Metered API key (both username AND credential)
- `turn` → `turn-us-east` (if using US East region, etc.)

### Step 5: Commit and Deploy
```bash
git add render.yaml
git commit -m "Update TURN credentials to Metered.ca"
git push origin main  # Or your branch name
# Render auto-redeploys
```

### Step 6: Verify
1. Wait 2-3 minutes for Render build
2. Test call on multiple networks
3. Check debug panel path shows `relay`

---

## Option 2: Twilio (Enterprise-Grade)

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/console
2. Sign up for free trial ($15 credit)
3. Verify phone number
4. Go to Console dashboard

### Step 2: Get Credentials
1. Dashboard → Account Info (right sidebar)
2. Copy **Account SID**: `ACxxxxxxxxxxxxxxxx`
3. Copy **Auth Token**: `a1b2c3d4e5f6g7h8i9j0...` (click eye icon to reveal)

**Keep these SECRET!** (Like a password)

### Step 3: Find TURN URL
Twilio provides global TURN:
```
turn:global.turn.twilio.com:3478 (UDP)
turn:global.turn.twilio.com:443 (TCP/TLS)
```

### Step 4: Update render.yaml

**New (Twilio):**
```yaml
- key: WEBRTC_ICE_SERVERS_JSON
  value: '[{"urls":["stun:stun.l.google.com:19302","stun:stun1.l.google.com:19302"]},{"urls":"turn:global.turn.twilio.com:3478","username":"ACxxxxxxxxxxxxxxxx","credential":"a1b2c3d4e5f6g7h8i9j0..."},{"urls":"turn:global.turn.twilio.com:443?transport=tcp","username":"ACxxxxxxxxxxxxxxxx","credential":"a1b2c3d4e5f6g7h8i9j0..."}]'
```

**Replace:**
- `ACxxxxxxxxxxxxxxxx` → Your Twilio Account SID
- `a1b2c3d4e5f6g7h8i9j0...` → Your Twilio Auth Token

### Step 5: Commit and Deploy
```bash
git add render.yaml
git commit -m "Update TURN credentials to Twilio"
git push origin main
# Render auto-redeploys
```

### Step 6: Setup Monitoring (Optional)
1. Twilio Console → Insights
2. Monitor TURN usage
3. Upgrade plan if needed (pay-as-you-go available)

---

## Option 3: Self-Hosted Coturn (Advanced)

### When to Use:
- High call volume (1000+ concurrent calls)
- Need extreme control
- Have spare VPS budget

### Quick Setup:

#### 3a: Rent VPS
- Provider: Linode, DigitalOcean, AWS, Hetzner
- Size: 1 CPU, 1 GB RAM minimum ($5-10/mo)
- OS: Ubuntu 20.04 LTS
- Note IP address: `1.2.3.4`

#### 3b: Install Coturn
SSH into VPS:
```bash
sudo apt-get update
sudo apt-get install coturn -y
sudo nano /etc/coturn/turnserver.conf
```

Edit config (key parts):
```
realm=1.2.3.4  # Your VPS IP
listening-ip=0.0.0.0
listening-port=3478
listening-port=80
listening-port=443
tls-listening-port=5349
tls-listening-port=443
user=username:password  # Set your credentials
```

Start server:
```bash
sudo systemctl restart coturn
sudo systemctl enable coturn
```

#### 3c: Update render.yaml

**New (Self-Hosted):**
```yaml
- key: WEBRTC_ICE_SERVERS_JSON
  value: '[{"urls":["stun:1.2.3.4:3478"]},{"urls":"turn:1.2.3.4:80","username":"username","credential":"password"},{"urls":"turns:1.2.3.4:443","username":"username","credential":"password"}]'
```

**Replace:**
- `1.2.3.4` → Your VPS IP
- `username` → Your chosen username
- `password` → Your chosen password

#### 3d: Deploy and Test
```bash
git add render.yaml
git commit -m "Update TURN to self-hosted Coturn"
git push origin main
```

---

## Troubleshooting Credential Changes

### "Path still shows unknown"
- Wait 2 minutes for Render build to complete
- Reload video call page (hard refresh: Ctrl+Shift+R)
- TURN takes time to connect first call

### "ICE still shows failed"
- Check credentials are correct in render.yaml
- Verify server is reachable (ping test)
- Check firewall allows 3478, 80, 443, 5349
- Try different endpoint (UDP vs TCP)

### "Credentials don't work"
- Double-check copy/paste (no extra spaces)
- Verify provider account is active (not expired)
- Test in browser console:
  ```javascript
  // Chrome DevTools Console:
  const iceServers = JSON.parse(document.getElementById('webrtc-ice-servers').textContent);
  console.log(iceServers);  // Should show your new servers
  ```

### "Still using old credentials"
1. In Render dashboard: Build → Deployment
2. Scroll to environment variables
3. Verify WEBRTC_ICE_SERVERS_JSON shows new value
4. If old value shown: Manual redeploy (Render UI → Redeploy)

---

## Security Notes

### For Production:
1. **Store credentials in Render environment only** (NOT in git)
2. **Never commit real credentials to GitHub**
3. **Use role-based access** if using enterprise providers
4. **Rotate credentials quarterly**

### In render.yaml:
```yaml
# ✅ CORRECT: Reference env variable
- key: WEBRTC_ICE_SERVERS_JSON
  value: <actual credentials here>  # Render handles as secret

# ❌ WRONG: Committing to git
# Don't put in source code files!
```

---

## Cost Estimation

### Per 1000 Calls:

| Provider | Cost | Notes |
|----------|------|-------|
| **Metered.ca** | ~$2.50 | 1 hour relay per call @ $0.05/GB |
| **Twilio** | ~$0.40-4 | $0.04 signaling + $0 TURN (first 100,000 min) |
| **Self-Hosted** | ~$5-10 | VPS cost only, unlimited calls |

**Recommendation:**
- **Small (10-100 calls/mo):** Metered.ca (pay-as-you-go)
- **Medium (100-1000 calls/mo):** Twilio trial or Metered plan
- **Large (1000+ calls/mo):** Self-hosted or Twilio enterprise

---

## Verification Checklist

After credential replacement:

```
✅ render.yaml updated with new WEBRTC_ICE_SERVERS_JSON
✅ Credentials valid (tested on provider dashboard)
✅ Git pushed to trigger Render build
✅ Build completed (check Render Deployments tab)
✅ Fresh page load (Ctrl+Shift+R) on video call
✅ New TURN servers appear in browser console:
   > JSON.parse(document.getElementById('webrtc-ice-servers').textContent)
✅ Test call on different network
✅ Debug panel shows Path: relay
✅ Audio/video flows successfully
✅ No console errors
```

---

## Rollback (If Needed)

If new credentials don't work:

1. Revert to openrelay.metered.ca (temporary):
   ```yaml
   - key: WEBRTC_ICE_SERVERS_JSON
     value: '[{"urls":"turn:openrelay.metered.ca:80","username":"openrelayproject","credential":"openrelayproject"}]'
   ```

2. Commit and push
3. Investigate issue
4. Try again with corrections

---

## Support Resources

**Metered.ca:** https://www.metered.ca/docs  
**Twilio:** https://www.twilio.com/docs/voice/recording  
**Coturn:** https://github.com/coturn/coturn/wiki  

---

## Next Steps

1. Choose provider (Metered recommended)
2. Get credentials
3. Update render.yaml
4. Push to git
5. Test on multiple networks
6. Monitor for 24 hours
7. Upgrade if needed

**Status: Ready for production credential setup**
