# Enhanced Configuration Flow - Auto Station Discovery

## Overview

The integration now includes an **enhanced configuration flow** that:

1. **Links to EnBW Map**: Guides users directly to the official EnBW charging station map
2. **Auto-Fetches Station Details**: Automatically retrieves all charge point information
3. **Let's Users Select Points**: Choose which specific charge points to monitor
4. **No Manual ID Lookup**: All EVSE IDs are automatically extracted

## Configuration Steps

### Step 1: Choose Configuration Method

Users can choose to:
- **Browse Map & Enter ID** (Recommended): Opens EnBW map link in new tab, then enter station ID
- **Enter Station ID Directly**: Skip opening the map and just enter the ID

```
┌─────────────────────────────────────┐
│ How would you like to configure?    │
├─────────────────────────────────────┤
│ ○ Browse Map & Enter Station ID     │
│ ○ Enter Station ID Directly         │
└─────────────────────────────────────┘
```

### Step 2: Browse Map (Optional)

If user selects "Browse Map":

```
┌──────────────────────────────────────────────────┐
│ Browse EnBW Charging Map                         │
├──────────────────────────────────────────────────┤
│ Open this link to find stations:                │
│                                                  │
│ [Link to EnBW Map]                              │
│                                                  │
│ Note the station ID (6-digit number) and        │
│ proceed to the next step.                       │
│                                                  │
│ [Continue]                                      │
└──────────────────────────────────────────────────┘
```

### Step 3: Enter Station ID

User enters the station ID found on the map:

```
┌──────────────────────────────────────────────────┐
│ Enter Station ID                                 │
├──────────────────────────────────────────────────┤
│ Station ID: [171042_________]                   │
│                                                  │
│ Example: 171042 for BEG Abt Tor 5               │
│ [Cancel] [Submit]                               │
└──────────────────────────────────────────────────┘
```

**Behind the scenes:**
- Integration fetches data from API
- Validates station exists
- Extracts all charge point information

### Step 4: Select Charge Points

Integration shows all available charge points with details:

```
┌──────────────────────────────────────────────────┐
│ Select Charge Points                             │
├──────────────────────────────────────────────────┤
│ Station: BEG Abt Tor 5                          │
│ Found 6 charge points                           │
│                                                  │
│ Select which to monitor:                        │
│ ☑ Point 1 (TYPE2, 11kW)                        │
│ ☑ Point 2 (TYPE2, 11kW)                        │
│ ☑ Point 3 (CCS, 50kW)                          │
│ ☐ Point 4 (TYPE2, 11kW)                        │
│ ☑ Point 5 (TYPE2, 11kW)                        │
│ ☑ Point 6 (CCS, 50kW)                          │
│                                                  │
│ [Cancel] [Submit]                               │
└──────────────────────────────────────────────────┘
```

**Information auto-fetched from API:**
- EVSE ID: `DE*RBO*EEEB0258*1001`
- Connector Type: `TYPE2`, `CCS`, etc.
- Power: `11kW`, `50kW`, etc.
- Location: GPS coordinates, address
- Current Status: Available, Occupied, etc.

### Step 5: Configure Settings

Set update interval and finalize:

```
┌──────────────────────────────────────────────────┐
│ Configure Settings                               │
├──────────────────────────────────────────────────┤
│ Update Interval: [300_______________] seconds   │
│                                                  │
│ Range: 60 - 3600 seconds                        │
│ Default: 300 seconds (5 minutes)                │
│                                                  │
│ [Cancel] [Create]                               │
└──────────────────────────────────────────────────┘
```

## Data Automatically Fetched

When a user selects a station, the integration automatically retrieves:

```json
{
  "station_id": "171042",
  "station_name": "BEG Abt Tor 5",
  "charge_points": [
    {
      "evse_id": "DE*RBO*EEEB0258*1001",
      "name": "Point 1",
      "connector_type": "TYPE2",
      "power": 11,
      "status": "Available",
      "location": {
        "latitude": 48.7758,
        "longitude": 9.1829,
        "address": "Abt. Tor 5, Stuttgart"
      }
    },
    // ... more charge points
  ]
}
```

**No manual EVSE ID lookup required!** Everything is automatic.

## Configuration Entry Structure

The resulting config entry stores:

```python
entry.data = {
    "charging_stations": [
        {
            "station_id": "171042",
            "station_name": "BEG Abt Tor 5",
            "charge_points": [
                {
                    "evse_id": "DE*RBO*EEEB0258*1001",
                    "name": "Point 1",
                    "connector_type": "TYPE2",
                    "power": 11,
                    "location": {...}
                },
                // ... selected points only
            ]
        }
    ],
    "update_interval": 300
}
```

## Adding More Stations

After initial setup, users can add more stations via Options:

1. Settings → Devices & Services → EnBW Charging
2. Click Options
3. Select "Add Station"
4. Repeat the station selection process

Or use the service call:

```yaml
service: enbw_charging.add_charging_point
data:
  station_id: "171037"
```

## Error Handling

### Station Not Found

```
Connection Error
Failed to connect to EnBW API. Please verify the station ID from the map.
```

- Station ID doesn't exist
- EnBW API is down
- Network timeout

**Solution**: Verify station ID on the map, wait, and try again

### No Charge Points

```
Invalid Station
Station has no charge points available.
```

**Solution**: Use a different station

## Benefits of This Approach

✅ **No Manual Lookup**: Users don't need to find EVSE IDs manually  
✅ **Direct Map Link**: Easy access to official EnBW map  
✅ **Selective Monitoring**: Choose exactly which points to monitor  
✅ **Auto-Enriched Data**: All location and power data included  
✅ **Validation**: Station and charge points verified before saving  
✅ **User-Friendly**: Step-by-step guided process  

## Technical Details

### API Call Flow

```
User enters station ID
        ↓
Frontend validates (not empty)
        ↓
_fetch_station_details() called
        ↓
API: GET /chargestations/{stationId}
        ↓
Parse response
        ↓
Extract all charge points
        ↓
Display to user for selection
        ↓
Save selected charge points
```

### Methods Implemented

- `async_step_user()` - Choose config method
- `async_step_browse_map()` - Show map link
- `async_step_enter_station_id()` - Input station ID
- `async_step_select_charge_points()` - Select points
- `async_step_configure_settings()` - Set interval
- `_fetch_station_details()` - Fetch from API
- `_build_charge_points_schema()` - Build selection form

## Notes

- Charge point data is stored in the config entry for quick access
- The coordinator still fetches real-time status from the API
- Users can still add stations manually via service calls
- The options flow allows adding more stations a any time
