# EnBW EV Charging Stations Integration

A Home Assistant integration for monitoring EnBW electric vehicle charging stations in Germany.

## Features

- **Easy Configuration**: Add/remove charging stations via the UI or YAML
- **Real-time Status**: Get live status updates for all charging points
- **Occupancy Tracking**: View occupancy patterns by day of week and hour
- **Location Data**: GPS coordinates and addresses for all stations
- **Dynamic Icons**: Icons that change based on charging point status
- **Automatic Token Refresh**: Handles API token management automatically

## Installation

1. Download the integration files into your `custom_components` directory:
   ```
   /custom_components/enbw_charging/
   ```

2. Restart Home Assistant

3. Add the integration through Settings → Devices & Services → Create Integration

## Configuration

### Via UI

1. Go to Settings → Devices & Services
2. Click "Create Integration"
3. Search for "EnBW EV Charging"
4. Enter your charging station IDs and update interval

### Via YAML

```yaml
enbw_charging:
  charging_stations:
    - station_id: "171042"
      station_name: "BEG Abt Tor 5"
  update_interval: 300
```

## Getting Station IDs

To get your EnBW station IDs and authentication token, see:
https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573

## API Endpoints

The integration uses the EnBW public API:
- Base URL: `https://enbw-emp.azure-api.net/emobility-public-api/api/v1`
- Endpoint: `/chargestations/{stationId}`

## Entities

### Sensors

- **Status**: Current status of each charge point (Available, Occupied, Faulted, Unavailable, Reserved)
- **Occupancy**: Overall occupancy percentage for the station

### Binary Sensors

- **Available**: True if charge point is available for use
- **Occupied**: True if charge point is currently in use

### Attributes

All entities include the following attributes:
- `latitude`: GPS latitude
- `longitude`: GPS longitude
- `address`: Physical address
- `occupancy_weekday`: Occupancy percentage by day of week
- `occupancy_hourly`: Occupancy percentage by hour
- `evse_id`: Unique EVSE identifier
- `status`: Raw status from API

## Service Calls

### Add Charging Point

```yaml
service: enbw_charging.add_charging_point
data:
  station_id: "171042"
  station_name: "New Station"
```

### Remove Charging Point

```yaml
service: enbw_charging.remove_charging_point
data:
  station_id: "171042"
```

### Refresh Data

```yaml
service: enbw_charging.refresh_data
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

### Log occupancy patterns

```yaml
automation:
  - alias: "Log station occupancy"
    trigger:
      platform: time
      at: "23:59:59"
    action:
      - service: logger.set_level
        data:
          homeassistant.components.enbw_charging: debug
```

## Troubleshooting

### No entities created

- Check that your station ID is correct
- Verify internet connectivity
- Review Home Assistant logs for errors
- Test the API manually with your station ID

### Data not updating

- Check the update interval setting
- Verify the API is accessible
- Restart the integration

### API errors

- Verify your authentication token is correct
- Check that the station ID exists
- Ensure proper headers are being sent

## Development

For detailed API documentation and community discussions:
- [EnBW Charging Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)
- [EnBW EMP API Documentation](https://www.enbw.com/)

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please open an issue on the repository.
