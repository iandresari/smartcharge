# Integration Architecture

## Overview

The EnBW Charging integration follows the Home Assistant integration structure and design patterns.

## Directory Structure

```
enbw_charging/
├── __init__.py           # Integration entry point
├── manifest.json         # Integration metadata
├── const.py              # Constants and configuration
├── coordinator.py        # Data fetching and caching
├── config_flow.py        # UI configuration flow
├── sensor.py             # Sensor entities
├── binary_sensor.py      # Binary sensor entities  
├── services.py           # Custom service handlers
├── strings.json          # UI translations base
├── README.md             # User documentation
├── CONFIGURATION.md      # Configuration examples
├── LICENSE               # MIT License
├── py.typed              # PEP 561 type hints marker
└── translations/
    └── en.json          # English translations
```

## Component Responsibilities

### `__init__.py`
- Setup integration entry
- Initialize coordinator
- Manage platform setup
- Handle unload

### `coordinator.py` (EnBWChargingCoordinator)
- Extend DataUpdateCoordinator
- Fetch data from EnBW API
- Cache charge point status
- Track occupancy history
- Calculate statistics (by weekday/hour)

### `config_flow.py` (EnBWChargingConfigFlow)
- Step-by-step configuration UI
- Station ID validation
- API connectivity testing
- Store configuration in config entries

### `sensor.py`
- ChargePointStatusSensor: Individual point status
- StationOccupancySensor: Overall station occupancy %
- Include extra attributes: location, occupancy history

### `binary_sensor.py`
- ChargePointAvailabilityBinarySensor: True if available
- ChargePointOccupiedBinarySensor: True if occupied
- Dynamic icons based on status

### `services.py`
- Add charging point service
- Remove charging point service
- Manual refresh service

### `const.py`
- API URLs and headers
- Configuration keys
- Status mappings
- Icon definitions
- Service names

## Data Flow

```
Home Assistant Core
    ↓
Config Entry
    ↓
EnBWChargingConfigFlow (config_flow.py)
    ↓
__init__.py → async_setup_entry()
    ↓
EnBWChargingCoordinator (coordinator.py)
    ↓
API: EnBW ← → HTTP Requests (aiohttp)
    ↓
Charge Points Data
    ↓
Entities (sensor.py, binary_sensor.py)
    ↓
Home Assistant State Machine
    ↓
Automations, Dashboard, Services
```

## Data Update Cycle

1. **Coordinator Initialization**
   - Creates DataUpdateCoordinator with 5min update interval
   - Stores config entry reference

2. **Periodic Update** (every 300 seconds)
   - `_async_update_data()` called by coordinator
   - For each configured station:
     - Fetch station data via `_fetch_station_data()`
     - Update occupancy history via `_update_occupancy_history()`
   - Return consolidated data

3. **Entity Updates**
   - Entities notified of coordinator update
   - Fetch new values from coordinator.data
   - Update Home Assistant state

4. **History Tracking**
   - Store hourly occupancy per charge point
   - Calculate weekday/hourly statistics
   - Keep 24h rolling window

## Configuration Storage

Configuration stored in config_entries:

```python
entry.data = {
    "charging_stations": [
        {
            "station_id": "171042",
            "station_name": "BEG Tor 5"
        }
    ],
    "update_interval": 300
}
```

## Entity IDs Generated

For station 171042 with charge point DE*RBO*EEEB0258*1001:

- **Sensor Status**: `sensor.beg_tor_5_de_rbo_eeeb0258_1001_status`
- **Binary Sensor Available**: `binary_sensor.beg_tor_5_de_rbo_eeeb0258_1001_available`
- **Binary Sensor Occupied**: `binary_sensor.beg_tor_5_de_rbo_eeeb0258_1001_occupied`
- **Occupancy Sensor**: `sensor.beg_tor_5_occupancy`

## API Integration

### Base Configuration

```python
API_BASE_URL = "https://enbw-emp.azure-api.net/emobility-public-api/api/v1"
headers = {
    "User-Agent": "Home Assistant / EnBW Charging Integration",
    "Ocp-Apim-Subscription-Key": "d4954e8b2e444fc89a89a463788c0a72",
    "Referer": "https://www.enbw.com/",
    "Origin": "https://www.enbw.com",
}
```

### Endpoints Used

- `GET /chargestations/{stationId}` - Fetch station data

### Response Example

```json
{
  "chargePoints": [
    {
      "evseId": "DE*RBO*EEEB0258*1001",
      "status": "Available",
      "location": {
        "latitude": 48.7758,
        "longitude": 9.1829,
        "address": "Abt. Tor 5"
      },
      "powerKw": 11,
      "connectorType": "TYPE2"
    }
  ]
}
```

## Error Handling

- TimeoutError: Logged but doesn't break coordinator
- Connection errors: Coordinator report as Failed
- Invalid status: Gracefully defaults to UNKNOWN
- Missing location: Defaults to 0, 0

## Occupancy Statistics

### By Weekday
- Tracks each day 0-6 (Mon-Sun)
- Counts occupied vs total charge points
- Calculates percentage

### By Hour
- Tracks each hour 0-23
- Aggregates data over 24h window
- Provides hourly occupancy trends

## Icon Mapping

| Status | Icon |
|--------|------|
| Available | mdi:ev-station |
| Occupied | mdi:ev-station-unavailable |
| Faulted | mdi:alert-circle |
| Unavailable | mdi:cancel |
| Reserved | mdi:lock |

## Extensions

Future expansion points:
- Reservation system integration
- Price/tariff information
- Energy consumption tracking
- Real-time availability notifications
- Mobile app integration
- Calendar scheduling
