# Multi-Network Testing & Troubleshooting Guide

## Testing Matrix

### Network Type 1: Home WiFi (Direct Path)

**Setup:**
- Caller: WiFi on router
- Receiver: Same WiFi network OR different WiFi
- Expected: Direct P2P or relay (depends on `forceRelay` setting)

**Test Steps:**
1. Open debug panel, note starting states
2. Initiate call from Caller → Receiver
3. Wait 2-3 seconds for media negotiation
4. **Check debug panel:**
   - Socket: `open` ✅
   - Signaling: `stable` ✅
   - ICE Conn: `connected` or `completed` ✅
   - Peer Conn: `connected` ✅
   - Path: `relay` (force relay on) OR `direct` (force relay off) ✅

5. **Audio/Video test:**
   - Speak into mic - other user should hear
   - Both video feeds should display
   - Audio should be clear

**Expected Result:** Media flows, path shows relay/direct correctly

---

### Network Type 2: Mobile Data (Cellular)

**Setup:**
- Caller: WiFi on home router
- Receiver: 4G/5G mobile data
- OR Both on separate mobile networks

**Test Steps:**
1. Disconnect mobile receiver from WiFi
2. Connect via 4G/5G data only
3. Open browser, go to video call room
4. Wait for participant connection
5. Check debug panel same as above

**Expected Behavior:**
- **Before:** NAT translation at mobile carrier gateway
- **With TURN:** Relay through openrelay.metered.ca or your TURN server
- Path: `relay` ✅ (TURN active)
- Media: Should flow without interruption

**Troubleshooting if failed:**
- Check browser console for errors
- Verify mobile network allows WebSocket (port 443)
- Try switching to 4G if 5G fails (less common)

---

### Network Type 3: Restrictive Network (Corporate VPN, Public WiFi)

**Setup:**
- Caller: WiFi at coffee shop / office VPN
- Receiver: Home WiFi
- Restrictive rules: Blocks UDP, allows only TCP 443

**Test Steps:**
1. Connect to restrictive network (or simulate)
2. Open browser, go to video call
3. Note initial ICE gathering
4. Monitor debug panel during negotiation

**Expected Behavior:**
- Direct P2P attempt fails (UDP 19302 blocked)
- ICE state shows: `disconnected` → `failed` (briefly)
- Relay fallback kicks in (after ~800ms)
- RTCConfig changes to `iceTransportPolicy: 'relay'`
- TURN server contacted over TCP 443 + TLS
- Path: `relay` ✅

**Why TCP 443 + TLS works:**
- Port 443 (HTTPS) almost always allowed
- TLS encryption bypasses deep packet inspection
- `turns:openrelay.metered.ca:443?transport=tcp`

---

### Network Type 4: Two Peers, Same Network (Important!)

**Setup:**
- Caller: PC on home WiFi (192.168.1.5)
- Receiver: Mobile on same WiFi (192.168.1.10)
- OR: Two PCs on same corporate network

**Test Steps:**
1. Both connect to same WiFi
2. Both go to skill-swap (different users)
3. Initiate call between them
4. Monitor debug panel

**Expected Behavior:**
- ICE gathering finds both direct and relay candidates
- With `forceRelay: true` → Only relay candidates considered
- Path: `relay` (TURN used despite same network)
- Media: Flows through TURN server (not P2P)

**Benefit of Force Relay:**
- Consistent performance regardless of network topology
- Predictable behavior for debugging
- No complex P2P negotiation edge cases

---

## Real-Time Diagnostics

### Debug Panel State Transitions

#### Healthy Call (Target State):
```
Initial Join:
  Socket: connecting → open
  Signaling: new → have-local-offer → stable
  ICE Conn: new → checking → connected → completed
  Peer Conn: new → connecting → connected
  Path: unknown → relay / direct

During Call:
  Socket: open ✅
  Signaling: stable ✅
  ICE Conn: connected / completed ✅
  Peer Conn: connected ✅
  Path: relay / direct ✅
```

#### Problem States:

**Socket: closed / closing**
- WebSocket dropped
- Network connectivity issue
- Server unreachable
- **Action:** Check internet, reload page

**Signaling: have-local-offer (stuck)**
- Offer not sent via WebSocket
- Receiver hasn't responded
- **Action:** Wait 5 sec, then check browser console

**ICE Conn: failed (hard failure)**
- All ICE candidates exhausted
- No direct path AND no TURN accessibility
- **Action:**
  1. Verify TURN server credentials in render.yaml
  2. Check if TURN server endpoint is accessible (ping test)
  3. Restart page and try again

**Peer Conn: failed**
- Media connection established but failed
- Usually caused by ICE failure or SDP negotiation error
- **Action:**
  1. Check ICE Conn state
  2. Restart ICE automatically triggered
  3. If persists, check browser console for errors

**Path: unknown (persistent)**
- Stats polling unable to determine connection type
- Could indicate very restrictive network
- **Action:**
  1. If audio/video works, still okay
  2. Check if TURN server is active (should show relay eventually)

---

## Browser Console Debugging

### Enable Console Logging:
Press `F12` → Console tab

### Key Log Messages:

**Healthy:**
```
Video WebSocket connected
participant_joined: <username>
ice_candidate: ... (multiple lines)
offer sent
answer received
```

**Problems to Watch:**
```
❌ "Failed to add ICE candidate: [error]"
   → Likely ICE timing issue (candidate before SDP)
   → Usually recovers automatically

❌ "Video WebSocket closed unexpectedly"
   → Connection to server lost
   → Check network, reload page

❌ "Error accessing media devices"
   → Browser permission denied for camera/mic
   → Check browser permissions in address bar

❌ "Negotiation failed: [error]"
   → Offer/answer SDP creation failed
   → Rare, but check RTC configuration
```

---

## Network Simulation (Advanced Testing)

### Using Browser DevTools:

1. Open DevTools (F12) → Network tab
2. Click "Offline" dropdown → Select network type:
   - Fast 3G
   - Slow 3G
   - Offline

3. Test with throttling enabled
4. Watch debug panel for adaptation

### Using Firewall Rules (Windows):

To simulate blocked UDP (force TURN usage):

```powershell
# Block UDP 19302 (STUN)
New-NetFirewallRule -DisplayName "Block STUN" -Direction Outbound -Action Block -Protocol UDP -RemotePort 19302

# Remove rule later:
Remove-NetFirewallRule -DisplayName "Block STUN"
```

---

## Render Logfile Monitoring

After deployment, monitor server logs:

### Render Dashboard:
1. Go to https://dashboard.render.com
2. Select "skill-swap" service
3. Click "Logs" tab
4. Search for errors

### Key Server Logs to Check:

```
✅ Daphne/ASGI startup: "Listening on [::]:10000" or similar
✅ First WebSocket connect: (Usually silent, or DEBUG=true logs it)
✅ No 500 errors in Render logs

❌ "None is not json serializable" → ICE server config issue
❌ "Connection refused" → Database issue
❌ WebSocket 404 errors → Routing issue
```

---

## Troubleshooting Flowchart

```
Video Call Failed? 
│
├─ Media not flowing?
│  └─ Check debug panel
│     ├─ Socket NOT open?
│     │  └─ Network connectivity issue → Reload page
│     ├─ Signaling NOT stable?
│     │  └─ Offer/answer stuck → Check console, reload
│     ├─ ICE Conn failed?
│     │  └─ Direct path blocked, relay failed
│     │     ├─ Check TURN credentials in render.yaml
│     │     ├─ Verify TURN server accessible
│     │     └─ Try different network
│     └─ Peer Conn connected but no media?
│        └─ Video track issue → Check permissions
│
├─ Can't get permission for camera/mic?
│  └─ Browser permissions
│     ├─ Check address bar lock icon → Site settings
│     ├─ Reload page after granting permission
│
└─ Persistent failures on specific network?
   └─ This network likely blocks media ports
      ├─ Use force relay (already enabled)
      ├─ Or use VPN to bypass network restrictions
```

---

## Performance Tuning

### If Latency Too High on Relay:

**Option 1: Try direct path** (if possible)
```javascript
// Modify video_room.html around line 180:
// iceTransportPolicy: 'all'  // Instead of 'relay'
// Then redeploy
```

**Option 2: Switch to closer TURN server**
- Current: `openrelay.metered.ca` (location: Netherlands)
- Alternative: Metered US data center
- Update WEBRTC_ICE_SERVERS_JSON with new endpoint

**Option 3: Replace with paid TURN provider**
- Twilio: Global edge network
- Metered: Multiple data centers
- See render.yaml documentation in WEBRTC_SETUP_VERIFIED.md

---

## Production Readiness Checklist

### Before Going Live:

```
✅ Tested on WiFi (local network)
✅ Tested on mobile data (different NAT)
✅ Tested on restrictive network (TCP 443 only)
✅ Tested from 2+ geographic regions
✅ Tested with 2-10 concurrent calls
✅ Monitored Render logs for errors
✅ Verified TURN server credentials work
✅ Audio/video quality acceptable
✅ Debug panel shows healthy states
✅ No console errors during normal usage
```

### For Production Deployment:

1. **Replace public TURN credentials** with own provider
2. **Update Render environment variables** with new credentials
3. **Redeploy** to Render
4. **Run load test** (5-10 concurrent calls)
5. **Monitor** for 24 hours for issues

---

## End-to-End Test Scenario

**Scenario: Test full call lifecycle**

```
Precondition:
- User A and User B already exist, registered
- Both logged in from different networks

Steps:
1. User A: Go to User B's profile
2. User A: Click "Start Video Call"
3. User B: See incoming call notification
4. User B: Join the call
5. [Wait 2-3 seconds for media negotiation]
6. Check debug panel:
   - Socket: open
   - Signaling: stable
   - Peer Conn: connected
   - Path: relay
7. Speak: "Can you hear me?"
8. User B: Confirm audio/video working
9. User A: Click "End Call"
10. System: Verify call ended, stats recorded

Success Criteria:
✅ Both users can hear each other
✅ Both video feeds display
✅ Debug states are healthy
✅ No console errors
✅ Call cleanup successful
```

---

## Collecting Debug Info for Support

If call fails after deployment, collect:

1. **Screenshot of debug panel** (showing all 6 states)
2. **Browser console errors** (F12 → Console → Copy all output)
3. **Render server logs** (Last 50 lines)
4. **Network info:**
   - WiFi / Mobile / Corporate VPN?
   - Geographic location?
   - ISP (if known)?
5. **Time of failure** (to cross-reference with server logs)

---

## Summary

- ✅ **STUN:** Google public STUN for NAT detection
- ✅ **TURN:** 6 endpoints (UDP/TCP/TLS combinations)
- ✅ **Force Relay:** Always use relay for consistency
- ✅ **ICE Exchange:** Full signaling via WebSocket
- ✅ **Recovery:** Auto-restart ICE on failure
- ✅ **Diagnostics:** Live 6-state panel + stats polling
- ✅ **Testing:** Multi-network scenarios covered

**Status: Ready for deployment and production testing.**
