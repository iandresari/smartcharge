# Quick Start Installation Guide

## Prerequisites

- Home Assistant 2024.1.0 or later
- Access to the file system (SSH, Samba, Studio Code Server, etc.)
- Valid EnBW charging station ID(s)

## Installation Methods

### Method 1: Manual Installation (Recommended for Development)

1. **SSH into your Home Assistant instance:**
   ```bash
   ssh root@homeassistant.local
   ```

2. **Navigate to custom components directory:**
   ```bash
   cd /config/custom_components
   ```

3. **Clone or download the integration:**
   ```bash
   git clone https://github.com/your-username/enbw-charging.git enbw_charging
   ```

   OR download as ZIP and extract to `enbw_charging/`

4. **Restart Home Assistant:**
   ```bash
   cd /config
   curl -X POST http://localhost:8123/api/services/homeassistant/restart \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json"
   ```

5. **Verify installation:**
   - Go to Settings → Developer Tools → States
   - Search for `enbw_charging` entities
   - They won't appear until you create the integration

### Method 2: HACS Installation (When Published)

1. Open Home Assistant
2. Go to HACS → Integrations
3. Click the "+" button
4. Search for "EnBW Charging"
5. Click "Install"
6. Restart Home Assistant

### Method 3: Using Studio Code Server

1. Open Studio Code Server in Home Assistant
2. Open the File Explorer
3. Navigate to `/config/custom_components/`
4. Create a new folder: `enbw_charging`
5. Upload all files from the repository
6. Restart Home Assistant

## Initial Setup

### Step 1: Find a Station ID

Need a valid EnBW station ID. Here are some known ones:
- 171042 - BEG Abt Tor 5
- 171037 - BEG Abt Tor 6
- 170884 - Stuttgart Markthalle
- 180081 - Karlsruhe Stadtcenter

Or search the [Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)

### Step 2: Create the Integration

1. Go to **Settings → Devices & Services**
2. Click **"Create Integration"** (or **"Create Automation"** then look for integrations)
3. Search for **"EnBW EV Charging"**
4. Click it and follow the wizard
5. Enter:
   - **Update Interval**: 300 (5 minutes) - can be 60-3600 seconds
   - Click **Create**

### Step 3: Add Charging Stations

After creating the integration:

1. Find the EnBW integration in Devices & Services
2. Click the integration entry
3. Click **"Options"** (or the settings icon)
4. Enter:
   - **Station ID**: e.g., `171042`
   - **Station Name**: e.g., `BEG Abt Tor 5`
5. Click **"Add Station"**
6. Repeat for additional stations

## Verification

After setup, you should see:

```
🎯 Sensors (created for each charge point):
- sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_status
- sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_status

🚨 Binary Sensors (created for each charge point):
- binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
- binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_available
- binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_occupied
- binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_occupied

📊 Occupancy Sensor:
- sensor.beg_abt_tor_5_occupancy
```

### Check Logs

To verify everything is working:

1. Go to **Settings → System → Logs**
2. Search for `enbw_charging`
3. Look for `"Setting up EnBW Charging integration"`
4. Check for any error messages

## Troubleshooting

### Entities Don't Appear

**Check the following:**

1. Is the station ID correct?
   ```bash
   # Test with curl
   curl "https://enbw-emp.azure-api.net/emobility-public-api/api/v1/chargestations/171042" \
     -H "Ocp-Apim-Subscription-Key: d4954e8b2e444fc89a89a463788c0a72"
   ```

2. Are you online? (Test with curl above)

3. Check Home Assistant logs for errors

4. Try restarting the integration:
   - Settings → Devices & Services
   - Find EnBW integration
   - Click the menu (three dots)
   - Reload

### API Connection Error

**Solutions:**
- Check internet connectivity
- Try a different station ID
- Verify the API key in the code (shouldn't need to change)
- Check if running behind a proxy/firewall

### Data Not Updating

**Check:**
1. The update interval is at least 60 seconds
2. Home Assistant has internet access
3. The API endpoint returns data (curl test)
4. Try refreshing manually:
   ```yaml
   service: enbw_charging.refresh_data
   ```

## First Automation

Create a simple test automation:

```yaml
automation:
  - alias: "Test EnBW Status"
    trigger:
      platform: state
      entity_id: binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
      to: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "Test"
          message: "Charging point available!"
```

This will create a notification when the first charge point becomes available.

## Next Steps

- Add the sensor to your dashboard
- Create automations based on availability
- Set up notifications
- Review CONFIGURATION.md for more examples

## Getting Help

- **Home Assistant Community**: [EnBW Charging Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)
- **Issues**: Create an issue on GitHub
- **Documentation**: See README.md and CONFIGURATION.md

---

**Installation Complete!** 🎉

Your EnBW charging station integration is now set up and running.
