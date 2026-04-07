# Getting Started Guide

## Installation

### Step 1: Install the Integration

**Option A: Manual Installation**
1. Download or clone the repository
2. Copy the `enbw_charging` folder to your Home Assistant `custom_components` directory:
   ```
   ~/.homeassistant/custom_components/enbw_charging/
   ```
3. Restart Home Assistant

**Option B: HACS Installation** (if published)
1. Open HACS
2. Search for "EnBW Charging"
3. Click "Install"
4. Restart Home Assistant

### Step 2: Create the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **"Create Integration"**
3. Search for **"EnBW EV Charging"**
4. Follow the setup wizard

### Step 3: Configure Charging Stations

In the setup wizard, you'll need to provide:
- **Station ID**: The numeric ID for an EnBW charging station
- **Station Name**: A friendly display name
- **Update Interval**: How often to fetch data (in seconds)

## Getting Your First Station ID

### Method 1: Community Thread
Visit the [Home Assistant Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573) which has a list of known station IDs.

### Method 2: Web API Discovery
You can test if a station exists by making a request:

```bash
curl -X GET \
  "https://enbw-emp.azure-api.net/emobility-public-api/api/v1/chargestations/171042" \
  -H "Ocp-Apim-Subscription-Key: d4954e8b2e444fc89a89a463788c0a72" \
  -H "User-Agent: Home Assistant" \
  -H "Referer: https://www.enbw.com/" \
  -H "Origin: https://www.enbw.com"
```

If you get a JSON response with `chargePoints`, the station ID is valid.

### Method 3: Browse EnBW Map
The EnBW website has an interactive map where you can find station IDs by looking at charging locations in your area.

## Verifying the Installation

Once installed, you should see:

1. **Config Entry**: EnBW EV Charging in Devices & Services
2. **No entities yet**: They're created after configuration
3. **Integration status**: Should show as "Loaded"

## First Setup - Multi-Step Wizard

The configuration flow guides you through 5 steps:

### Step 1: Choose How to Find Your Station
```
How would you like to configure?
○ Browse Map & Enter Station ID  (Recommended)
○ Enter Station ID Directly
```

**Recommended**: Browse the official EnBW map first

### Step 2: Browse EnBW Map
- Opens link in your browser: https://www.enbw.com/elektromobilitaet/produkte/mobilityplus-app/ladestation-finden/map
- Find your nearest charging station
- Note the station ID (6-digit number, e.g., **171042**)
- Click "Continue"

### Step 3: Enter Station ID
```
Station ID: [171042______________]
Example: 171042 for BEG Abt Tor 5
```

The integration will:
- ✅ Validate the station exists
- ✅ Fetch all charge point information
- ✅ Extract EVSE IDs automatically
- ✅ Display available charge points

### Step 4: Select Charge Points
The integration shows all charge points with details:
```
Station: BEG Abt Tor 5 (6 points found)

Select which to monitor:
☑ Point 1 - TYPE2 Connector, 11kW
☑ Point 2 - TYPE2 Connector, 11kW
☑ Point 3 - CCS Connector, 50kW
☐ Point 4 - TYPE2 Connector, 11kW
☑ Point 5 - TYPE2 Connector, 11kW
☑ Point 6 - CCS Connector, 50kW

[Select at least one]
```

**All information auto-fetched from API** - no manual lookup needed!

### Step 5: Configure Settings
```
Update Interval: [300_____________] seconds
Range: 60 - 3600 seconds
Default: 300 seconds (5 minutes)
```

Click "Create" and you're done! 🎉

## What Gets Created

After setup, you'll see entities for each selected charge point:

```
Entity Examples:
├── binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
├── binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_occupied
├── sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_status
├── sensor.beg_abt_tor_5_occupancy
└── Other charge points...
```

## Getting Your First Station ID

### Quick Method: Use the Configuration Wizard

1. Start creating the integration
2. Choose "Browse Map"
3. A link opens automatically
4. Find your station
5. Copy the station ID
6. Enter it in the wizard

### Alternative: Manual Search

1. Visit the map directly: https://www.enbw.com/elektromobilitaet/produkte/mobilityplus-app/ladestation-finden/map
2. Search for your city or location
3. Click on a charging station
4. The station ID appears in the URL or details
5. Note it down (e.g., **171042**)

### Known Station IDs

Popular stations to try:
- **171042**: BEG Abt Tor 5, Stuttgart
- **171037**: BEG Abt Tor 6, Stuttgart  
- **170884**: Stuttgart Markthalle
- **180081**: Karlsruhe Stadtcenter

Visit the [Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573) for more IDs.

## Verifying the Installation

Once configured, verify entities appear:

1. Go to **Developer Tools** → **States**
2. Search for `enbw_charging`
3. You should see:
   - Binary sensors for availability/occupancy
   - Sensors for status and occupancy %
   - All with attributes

**If nothing appears:**
- Check Home Assistant logs
- Verify station ID is correct
- Try a different station
- Check internet connectivity

## Next Steps

### Create a Dashboard Card

Add a simple card to see all your charge points:

```yaml
type: entities
title: "EV Charging Status"
entities:
  - binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
  - binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_available
  - sensor.beg_abt_tor_5_occupancy
```

### Create Your First Automation

```yaml
automation:
  - alias: "Notify when charging available"
    trigger:
      platform: state
      entity_id: binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
      to: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "Charger Available!"
          message: "Point 1 is now available"
```

### Add More Stations

After initial setup:
1. Go to Settings → Devices & Services
2. Find EnBW Charging integration
3. Click "Options"
4. Click "Add Station"
5. Follow setup for new station
