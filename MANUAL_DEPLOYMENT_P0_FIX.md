# Manual Deployment Guide: P0 BLE Presence Monitor Coroutine Fix

## Overview
This guide provides step-by-step instructions for manually deploying the P0 coroutine fix to resolve the BLE presence monitor TypeError that occurs every 60 seconds.

## Problem Description
- **Issue**: `TypeError("'coroutine' object is not iterable")` in bb8_presence_monitor logs
- **Frequency**: Every 60 seconds during BLE presence monitoring
- **Root Cause**: `asyncio.run()` called from within existing event loop in `mqtt_dispatcher.py`
- **Fix**: ThreadPoolExecutor wrapper to run coroutines in separate thread

## Fix Details
**File**: `addon/bb8_core/mqtt_dispatcher.py`
**Function**: `_get_scanner_publisher()` (lines ~196-220)
**Solution**: Added ThreadPoolExecutor to safely execute async functions from sync context

## Manual Deployment Steps

### Step 1: Prepare the Fixed File
The P0 fix is already committed to git with the message:
```
fix(P0): Resolve BLE presence monitor coroutine TypeError
```

### Step 2: Access Home Assistant Instance
```bash
# Connect to Home Assistant via SSH
ssh home-assistant
# or ssh hass (alternative alias)
```

### Step 3: Locate BB8 Addon Directory
The addon may be installed in one of these locations:
```bash
# Option A: Developer addon (if using local development)
/config/addons/local/ha-bb8/

# Option B: Supervisor managed addon
/usr/share/hassio/addons/local/ha-bb8/

# Option C: Custom addon directory
/addons/ha-bb8/
```

**Find the correct path:**
```bash
# Search for the addon directory
find / -name "bb8_core" -type d 2>/dev/null
# or
find /config -name "*bb8*" -type d 2>/dev/null
```

### Step 4: Backup Current File
```bash
# Navigate to addon directory (replace PATH with actual path from Step 3)
cd /PATH/TO/ha-bb8/addon/bb8_core/

# Create backup of current file
cp mqtt_dispatcher.py mqtt_dispatcher.py.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup
ls -la mqtt_dispatcher.py*
```

### Step 5: Apply the P0 Fix

**Option A: Direct File Transfer (Recommended)**
From your local machine:
```bash
# Copy fixed file to Home Assistant
scp /Users/evertappels/Projects/HA-BB8/addon/bb8_core/mqtt_dispatcher.py \
    home-assistant:/PATH/TO/ha-bb8/addon/bb8_core/mqtt_dispatcher.py
```

**Option B: Manual Edit**
If file transfer is not possible, manually edit the `_get_scanner_publisher()` function:

1. Open the file: `nano mqtt_dispatcher.py`
2. Find the `_get_scanner_publisher()` function (around line 196)
3. Replace the existing function with:

```python
def _get_scanner_publisher(bb8_facade: BB8Facade, mqtt_client) -> Callable[[], None]:
    """
    Get the scanner publisher function.
    
    Args:
        bb8_facade: The BB8 facade instance
        mqtt_client: The MQTT client instance
        
    Returns:
        A callable that publishes discovery when called
    """
    def publisher():
        try:
            # Check if we're already in an event loop
            try:
                asyncio.get_running_loop()
                # We're in an event loop, use ThreadPoolExecutor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, publish_discovery(bb8_facade, mqtt_client))
                    future.result(timeout=5)  # 5 second timeout
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                asyncio.run(publish_discovery(bb8_facade, mqtt_client))
        except Exception as e:
            logger.error(f"Failed to publish scanner discovery: {e}")
    
    return publisher
```

3. Save the file (Ctrl+X, Y, Enter in nano)

### Step 6: Restart BB8 Addon
```bash
# Restart the addon container (method depends on HA setup)

# Option A: Using HA CLI (if available)
ha addon restart local_ha-bb8

# Option B: Using docker (if accessible)
docker restart $(docker ps | grep bb8 | awk '{print $1}')

# Option C: Using Supervisor API
curl -X POST \
  -H "Authorization: Bearer YOUR_SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  http://supervisor/addons/local_ha-bb8/restart
```

### Step 7: Verify Fix Applied
Monitor the addon logs to confirm the TypeError is resolved:

```bash
# View recent logs
ha addon logs local_ha-bb8

# or if using docker
docker logs $(docker ps | grep bb8 | awk '{print $1}') --tail 50 --follow
```

**Expected Results:**
- ✅ No more `TypeError("'coroutine' object is not iterable")` messages
- ✅ BLE presence monitoring continues normally
- ✅ No 60-second interval error spam

### Step 8: Validation Test
Wait at least 2-3 minutes and check logs for:
1. Absence of coroutine TypeError
2. Normal BLE presence scanning messages
3. MQTT discovery publishing without errors

## Troubleshooting

### Issue: File Transfer Permission Denied
```bash
# Check file permissions and ownership
ls -la /PATH/TO/ha-bb8/addon/bb8_core/
# Adjust ownership if needed (replace with correct user)
chown homeassistant:homeassistant mqtt_dispatcher.py
```

### Issue: Addon Won't Restart
```bash
# Check addon status
ha addon info local_ha-bb8
# Force stop and start
ha addon stop local_ha-bb8
sleep 5
ha addon start local_ha-bb8
```

### Issue: Import Errors After Fix
```bash
# Verify Python syntax
python3 -m py_compile /PATH/TO/ha-bb8/addon/bb8_core/mqtt_dispatcher.py
# Restore backup if needed
cp mqtt_dispatcher.py.backup.TIMESTAMP mqtt_dispatcher.py
```

## Post-Deployment Verification

### Success Criteria
1. **No coroutine TypeError in logs** for at least 5 minutes
2. **BLE presence monitoring active** - should see scanning activity
3. **MQTT discovery publishing** - Home Assistant entities remain discoverable
4. **No regression in BB8 control** - existing functionality unchanged

### Log Monitoring Commands
```bash
# Monitor real-time logs for errors
ha addon logs local_ha-bb8 --follow | grep -i error

# Check for specific coroutine errors
ha addon logs local_ha-bb8 | grep -i "coroutine.*not iterable"

# Verify BLE scanning activity
ha addon logs local_ha-bb8 | grep -i "ble\|scan\|presence"
```

## Rollback Instructions
If the fix causes issues:

```bash
# Restore backup
cd /PATH/TO/ha-bb8/addon/bb8_core/
cp mqtt_dispatcher.py.backup.TIMESTAMP mqtt_dispatcher.py

# Restart addon
ha addon restart local_ha-bb8

# Verify rollback
ha addon logs local_ha-bb8 --tail 20
```

## Notes
- The fix is backward-compatible and should not affect existing functionality
- ThreadPoolExecutor provides safe coroutine execution from sync contexts
- 5-second timeout prevents hanging on slow BLE operations
- Error handling preserves existing logging behavior

## Next Steps After Successful Deployment
1. Monitor logs for 24 hours to ensure stability
2. Proceed with P1 BLE enhancements (ble_bridge.py improvements)
3. Update addon version and changelog
4. Consider automating deployment process for future fixes