# SmartCharge - EV Charging Station Monitor

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=iandresari&repository=smartcharge&category=integration)

A Home Assistant integration for monitoring EnBW electric vehicle charging stations in Germany.

## Features

- **Easy Configuration**: Add/remove charging stations via the UI
- **Real-time Status**: Get live status updates for all charging points
- **Occupancy Tracking**: View occupancy patterns by day of week and hour
- **Location Data**: GPS coordinates and addresses for all stations
- **Dynamic Icons**: Icons that change based on charging point status

## Installation

### HACS (Recommended)

1. Click the badge above, or go to HACS → Integrations → search for "SmartCharge"
2. Install the integration
3. Restart Home Assistant

### Manual

1. Download the integration files into your `custom_components` directory:
   ```
   custom_components/smartcharge/
   ```
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "SmartCharge"
4. Choose to browse the EnBW map or enter a station ID directly
5. Select which charge points to monitor
6. Configure the update interval (60–3600 seconds, default 300)

## Getting Station IDs

You can find station IDs by browsing the EnBW charging map during setup, or by visiting:

https://www.enbw.com/elektromobilitaet/produkte/mobilityplus-app/ladestation-finden/map

The station ID is the numeric identifier shown when you select a station on the map.

## Entities

### Sensors

- **Status**: Current status of each charge point (available, occupied, faulted, unavailable, reserved)
- **Occupancy**: Overall occupancy percentage for the station

### Binary Sensors

- **Available**: True if charge point is available for use
- **Occupied**: True if charge point is currently in use

### Attributes

Status sensors include:
- `evse_id`: Unique EVSE identifier
- `status`: Raw status from API
- `latitude` / `longitude`: GPS coordinates
- `address`: Physical address
- `power`: Charging power in kW
- `connector_type`: Connector type

Occupancy sensors include:
- `occupancy_weekday`: Occupancy percentage by day of week
- `occupancy_hourly`: Occupancy percentage by hour

Binary sensors include:
- `evse_id`, `status`, `latitude`, `longitude`, `address`

## Service Calls

### Add Charging Point

```yaml
service: smartcharge.add_charging_point
data:
  station_id: "171042"
  station_name: "New Station"
```

### Remove Charging Point

```yaml
service: smartcharge.remove_charging_point
data:
  station_id: "171042"
```

### Refresh Data

```yaml
service: smartcharge.refresh_data
```

## Status Icons

- 🟢 **Available**: `mdi:ev-station` - Ready to charge
- 🔴 **Occupied**: `mdi:ev-station-unavailable` - Currently in use
- ⚠️ **Faulted**: `mdi:alert-circle` - Technical issue
- ⭕ **Unavailable**: `mdi:cancel` - Not available
- 🔒 **Reserved**: `mdi:lock` - Reserved by another user

## Automations Example

### Notify when a specific station becomes available

```yaml
automation:
  - alias: "Notify when charging station available"
    trigger:
      platform: state
      entity_id: binary_sensor.beg_t5_1_available
      to: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Charging Station Available"
          message: "BEG Torhaus 5 Point 1 is now available!"
```

## Troubleshooting

### No entities created

- Check that your station ID is correct on the EnBW map
- Verify internet connectivity
- Review Home Assistant logs for errors (`custom_components.smartcharge`)

### Data not updating

- Check the update interval setting in the integration options
- Verify the API is accessible
- Restart the integration

## Development

For community discussions:
- [EnBW Charging Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please [open an issue](https://github.com/iandresari/smartcharge/issues).
