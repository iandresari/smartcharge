# SmartCharge - HACS Installation Guide

Users can now install SmartCharge directly from HACS!

## Installation Methods

### Method 1: HACS Store (Recommended)

**Requires**: HACS to be installed in Home Assistant

1. Open **Home Assistant**
2. Go to **HACS** in the sidebar
3. Click **Integrations**
4. Click the **+ Explore & Download Repositories** button
5. Search for **"SmartCharge"**
6. Click the **SmartCharge** card
7. Click **Download**
8. Select latest version
9. Click **Download**
10. Restart **Home Assistant**
11. Create the integration:
    - Settings → Devices & Services → Create Integration
    - Search for **"SmartCharge"**
    - Follow the setup wizard

### Method 2: Manual GitHub Installation

For manual installation or if HACS is not available:

```bash
# SSH into Home Assistant
ssh -i /path/to/key root@homeassistant.local

# or if using Home Assistant CLI
ha ssh

# Navigate to custom components
cd /config/custom_components

# Clone the repository
git clone https://github.com/iandresari/smartcharge.git smartcharge

# Or download as ZIP
wget https://github.com/iandresari/smartcharge/archive/refs/heads/main.zip
unzip main.zip
mv smartcharge-main/smartcharge smartcharge
rm -rf smartcharge-main main.zip
```

### Method 3: Samba/SCP File Share

If you have file access via Samba or SCP:

1. Mount/Access: `\\homeassistant\config\custom_components` (Samba) or `/config/custom_components` (SCP)
2. Create folder: `smartcharge`
3. Upload all files from the repository's `smartcharge/` folder
4. Restart Home Assistant

## After Installation

### Restart Home Assistant

1. Settings → System → **Restart Home Assistant**
2. Or click the restart button in HACS

### Create the Integration

1. Settings → Devices & Services
2. Click **Create Integration**
3. Search for **"SmartCharge"**
4. Follow the 5-step configuration wizard

### First Configuration

The wizard will guide you through:

1. **Choose method**: Browse map or enter ID directly
2. **Browse map**: Link to official EnBW charging map
3. **Enter station ID**: (e.g., 171042)
4. **Select charge points**: Choose which to monitor
5. **Settings**: Configure update interval

## Verification

After setup, verify installation:

1. Check **Developer Tools** → **States**
2. Search for `smartcharge`
3. Should see sensor and binary sensor entities
4. Check logs for any errors

## Troubleshooting

### Integration Not Showing

**Problem**: SmartCharge doesn't appear in integrations list

**Solutions**:
1. Restart Home Assistant: Settings → System → Restart
2. Hard refresh browser: Ctrl+Shift+R or Cmd+Shift+R
3. Check custom_components folder structure
4. Verify file permissions

### HACS Not Finding Repository

**Problem**: "SmartCharge" doesn't appear in HACS search

**Solutions**:
1. Ensure repository is public on GitHub
2. Wait 24-48 hours for HACS indexing
3. Manually add repository:
   - HACS → Integrations
   - Click menu (three dots)
   - **Custom repositories**
   - Add: `https://github.com/iandresari/smartcharge`
   - Category: **Integration**
   - Click **Create**

### API Connection Error During Setup

**Problem**: "Failed to connect to EnBW API"

**Solutions**:
1. Check internet connection
2. Verify station ID is correct
3. Try a different station ID
4. Check Home Assistant logs for details

### No Entities Created

**Problem**: After configuration, no sensors appear

**Solutions**:
1. Check Home Assistant logs
2. Verify station ID exists on [EnBW map](https://www.enbw.com/elektromobilitaet/produkte/mobilityplus-app/ladestation-finden/map)
3. Check configuration was saved correctly
4. Try selecting different charge points

## Updating SmartCharge

### Via HACS

1. HACS → Integrations
2. Find **SmartCharge**
3. If update available, click **Update**
4. Restart Home Assistant

### Manual Update

```bash
cd /config/custom_components/smartcharge
git pull origin main
# Restart Home Assistant
```

## File Structure Verification

After installation, your structure should be:

```
/config/custom_components/
└── smartcharge/
    ├── __init__.py
    ├── config_flow.py
    ├── const.py
    ├── coordinator.py
    ├── sensor.py
    ├── binary_sensor.py
    ├── services.py
    ├── manifest.json
    ├── strings.json
    ├── py.typed
    ├── requirements.txt
    ├── translations/
    │   └── en.json
    └── ... (other files)
```

**Important**: The integration folder must be named `smartcharge` (matches the domain)

## Requirements

- **Home Assistant**: 2024.1.0 or later
- **Python**: 3.9 or later
- **aiohttp**: Automatically installed
- **Internet**: Required for API communication

## Security Notes

✅ No credentials stored in code  
✅ API keys handled via Home Assistant secrets  
✅ All data traffic uses HTTPS  
✅ No personal data collected  

## Getting Help

- **Issues**: Create an issue on [GitHub](https://github.com/iandresari/smartcharge/issues)
- **Forum**: Post on [Home Assistant Community](https://community.home-assistant.io/)
- **Documentation**: See [GETTING_STARTED.md](./GETTING_STARTED.md)

## Next Steps

1. [Configure your first charging station](./GETTING_STARTED.md)
2. [Set up automations](./CONFIGURATION.md)
3. [Create dashboard cards](./README.md)

---

**Version**: 1.0.1  
**License**: MIT  
**Repository**: https://github.com/iandresari/smartcharge
