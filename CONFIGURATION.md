# EnBW Charging Stations - Example Configuration

## Example 1: Basic YAML Configuration
# Add this to your configuration.yaml or create a separate file and include it

```yaml
enbw_charging:
  charging_stations:
    - station_id: "171042"
      station_name: "BEG Abt Tor 5"
    - station_id: "171037"
      station_name: "BEG Abt Tor 6"
  update_interval: 300  # Update every 5 minutes
```

## Example 2: Import from REST API YAML
# Convert the example_rest_api.yaml format to this integration

```yaml
enbw_charging:
  charging_stations:
    # BEG Abt Tor 5
    - station_id: "171042"
      station_name: "BEG Abt Tor 5"
    # BEG Abt Tor 6
    - station_id: "171037"
      station_name: "BEG Abt Tor 6"
  update_interval: 300
```

## Example 3: Service Automation - Add Station Dynamically

```yaml
automation:
  - alias: "Add charging station via service"
    trigger:
      platform: time_pattern
      hours: "0"
      minutes: "0"
    action:
      - service: enbw_charging.add_charging_point
        data:
          station_id: "171042"
          station_name: "BEG Abt Tor 5"
```

## Example 4: Automations Based on Charge Point Availability

```yaml
automation:
  - alias: "Notify when BEG T5-1 becomes available"
    trigger:
      platform: state
      entity_id: binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
      to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Charging Station Available"
          message: "BEG Abt Tor 5 - Point 1 is now available!"
          data:
            entity_id: binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available

  - alias: "Log when charge points are occupied"
    trigger:
      platform: state
      entity_id: 
        - binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_occupied
        - binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_occupied
      to: "on"
    action:
      - service: logger.set_level
        data:
          enbw_charging: debug
```

## Example 5: Card Configuration for Home Assistant Dashboard

```yaml
type: grid
cards:
  - type: entity
    entity: sensor.beg_abt_tor_5_occupancy
    name: "Occupancy %"
    state_color: true

  - type: entities
    title: "Charge Points Status"
    entities:
      - binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available
      - binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_available
      - binary_sensor.beg_abt_tor_5_de_rbo_eeec0259_1001_available

  - type: custom:bar-chart-card
    title: "24h Occupancy Pattern"
    entities:
      - entity: sensor.beg_abt_tor_5_occupancy
        attribute: occupancy_hourly
```

## Example 6: History Statistics - Track Occupancy Over Time

```yaml
history_stats:
  - unique_id: beg_t5_1_occupied_today
    entities: binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_occupied
    state: "on"
    type: time
    period: day

  - unique_id: beg_t5_occupancy_percentage
    entities: sensor.beg_abt_tor_5_occupancy
    state: value
    type: mean
    period: day
```

## Example 7: Template Sensors for Advanced Logic

```yaml
template:
  - sensor:
      - name: "All Charging Available"
        unique_id: all_charging_available
        state: >
          {% set available = [
            is_state('binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1001_available', 'on'),
            is_state('binary_sensor.beg_abt_tor_5_de_rbo_eeeb0258_1002_available', 'on'),
            is_state('binary_sensor.beg_abt_tor_5_de_rbo_eeec0259_1001_available', 'on'),
          ] | select('equalto', True) | list %}
          {{ available | length }}

  - binary_sensor:
      - name: "Rush Hour Check"
        unique_id: rush_hour_check
        state: >
          {% set hour = now().hour %}
          {{ hour >= 12 and hour < 14 or hour >= 17 and hour < 19 }}
```

## Example 8: Conditional Alerts

```yaml
automation:
  - alias: "Alert if all points occupied during rush hour"
    trigger:
      platform: numeric_state
      entity_id: sensor.all_charging_available
      below: 1
    condition:
      condition: state
      entity_id: binary_sensor.rush_hour_check
      state: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "⚠️ All Charging Points Occupied"
          message: "During rush hour, all BEG Tor 5 charging points are occupied"
          notification_id: rush_hour_full
```

## Getting Your Station IDs

To find your charging station IDs:

1. Visit the [Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)
2. Use the EnBW website to browse available stations
3. Test the API endpoint: `https://enbw-emp.azure-api.net/emobility-public-api/api/v1/chargestations/{stationId}`

## API Response Structure

When the integration fetches data, it looks for:

```json
{
  "chargePoints": [
    {
      "evseId": "DE*RBO*EEEB0258*1001",
      "status": "Available",
      "location": {
        "latitude": 48.7758,
        "longitude": 9.1829
      },
      "address": "Abt. Tor 5",
      "connectorType": "TYPE2",
      "powerKw": 11
    }
  ]
}
```

Each charge point generates:
- **Sensor**: Shows current status
- **Binary Sensor (Available)**: True if status is "Available"
- **Binary Sensor (Occupied)**: True if status is "Occupied"
- **Attributes**: Location data, occupancy history
