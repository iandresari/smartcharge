
<p align="center">
  <img src="custom_components/smartcharge/brand/icon.png" alt="SmartCharge Icon" width="128" height="128">
</p>

# SmartCharge - EV Charging Station Monitor

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=iandresari&repository=smartcharge&category=integration)

A Home Assistant integration for monitoring EnBW electric vehicle charging stations in Germany and tracking how green the energy is when charging your EV.

## Features

- **Car Green-Charging Tracker**: Add your car and its GPS tracker to see live CO₂ intensity and accumulated charging stats using the [Electricity Maps](https://www.home-assistant.io/integrations/electricity_maps/) Home Assistant integration
- **Persistent Accumulators**: Energy, CO₂, and cost totals survive Home Assistant restarts — nothing is lost
- **Proximity-Based Billing**: Costs are automatically billed when the car is near a configured station. One-off session base fees are applied once per session start; per-kWh cost accrues continuously
- **Multiple Station Types**: EnBW public stations, custom home wallboxes, and temporary one-off stops — all handled with accurate billing
- **Auto-Discovery**: Optionally let SmartCharge detect nearby EnBW stations automatically while the car is charging and prompt you to add them
- **Easy Configuration**: Search nearby stations on a map or enter a station ID directly — one config entry per station
- **Custom Friendly Name**: Set a custom static part of the sensor's friendly name during setup or reconfiguration
- **Single Entity per Station**: One sensor per station showing `available` or `occupied`, with a dynamic name like `2 / 5 - StationName`. For stations with more than 9 charge points, the available count is spaced (e.g. `1 0 / 10 - StationName`)
- **Charge Point Details**: Every charge point's status, power, and connector type exposed as entity attributes
- **Occupancy Tracking**: Persistent occupancy histograms by hour-of-day and weekday, accumulating over time and surviving restarts
- **Map Integration**: GPS coordinates as attributes so the sensor appears on the HA map

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
4. **Choose what to add**: a **Car** (green-charging tracker) or a **Charging Station**

### Adding a Car

5. Enter a **Car Name**, the **Car Device Tracker** entity, the **Charging Power** sensor entity (in kW), an optional **Odometer** sensor (in km, for per-km stats), and the **CO₂ Intensity** entity (e.g. from the [Electricity Maps integration](https://www.home-assistant.io/integrations/electricity_maps/) — auto-selected if found)

Six sensors are created and grouped under a single device named after the car.

To track multiple cars, add the integration once per car.

### Adding a Charging Station

Choose from five station types:

#### Search Nearby Stations (Recommended)
Drag the map pin to your area, adjust the radius, pick a station from the results, and configure the update interval and tariff.

#### Browse EnBW Map & Enter Station ID
Manually look up a station on the EnBW map and enter its ID.

#### Find Station at Car's Current Location
Search for an EnBW station at the car's current GPS position. The search expands from 50 m → 100 m → 200 m until a station is found.

#### Temporary Station (removed after next drive)
Register a one-off charging stop using the car's **current GPS position** as the station location. The entry is automatically deleted once the car's odometer increases — i.e., after driving away. Requires at least one car entry to be configured.

#### Custom Wallbox
Add a fixed wallbox at the car's current GPS location. Provide a **live price entity** (ct/kWh) and optionally a **live CO₂ intensity entity** (gCO₂/kWh). When a CO₂ entity is provided it takes priority over the car's configured CO₂ entity. Requires at least one car entry to be configured.

> **Note**: Temporary stations and wallboxes create a lightweight config entry with no sensor entities. They exist solely to supply location and tariff data to the car tracker's proximity-billing logic.

### Auto-Discovery

When **Automatically discover charging stations while charging** is enabled in the car options, SmartCharge will search for nearby EnBW stations each time the car starts charging at an unrecognised location. If stations are found, a notification appears in the HA UI prompting you to add the station permanently. Only one discovery attempt is made per charging session.

## Car Tracking (Green Charging)

When you add a **Car** config entry, SmartCharge creates a **device** grouping six sensors per car. All sensors update together every poll cycle (≈ 5 minutes).

### Car Sensors

| Sensor | State | Unit | Icon |
|---|---|---|---|
| **CO2 Intensity** | Live grid CO₂ at the car's GPS location | gCO₂/kWh | `mdi:molecule-co2` |
| **Accumulated Energy** | Total kWh charged (persisted across restarts) | kWh | `mdi:ev-station` |
| **Accumulated CO2** | Total gCO₂ produced for that energy (persisted) | gCO₂ | `mdi:smog` |
| **Accumulated Cost** | Total charging cost — proximity billing (persisted) | EUR | `mdi:currency-eur` |
| **CO2 per km** | Average gCO₂ per km driven (requires odometer) | gCO₂/km | `mdi:leaf` |
| **Cost per km** | Average charging cost per km driven | EUR/km | `mdi:cash-marker` |

The CO2 Intensity sensor has no additional attributes. CO₂ and cost accumulators are persisted across restarts.

### Cost Billing (Proximity-Based)

When the car is within range of a configured station that has a tariff set, charging costs are billed automatically:

- A **base fee** (if configured) is added once when a new charging session begins
- A **per-kWh cost** accrues continuously while charging at that station
- A billing session ends when power drops to zero or the car moves away

For **wallboxes**, the price is read live from the configured price entity each poll cycle.  
For **temporary stations**, the tariff is fixed at the time of adding.

### Updating Car Settings

Use the integration entry → **Reconfigure** to update the car name, device tracker, power sensor, odometer sensor, CO₂ intensity entity, or auto-discovery toggle. The same settings are also accessible under **Configure** (Options).

## Getting Station IDs (Manual Fallback)

If you prefer to enter a station ID directly, you can find it using your browser's developer tools:

1. Open the [EnBW charging map](https://www.enbw.com/elektromobilitaet/produkte/mobilityplus-app/ladestation-finden/map)
2. Open your browser's developer tools (press `F12`), then go to the **Network** tab
3. Click on a charging station on the map
4. In the Network tab, look for a request to the EnBW API, e.g.:
   ```
   https://enbw-emp.azure-api.net/emobility-public-api/api/v1/chargestations/134057
   ```
5. The number at the end of the URL (e.g. `134057`) is the **station ID**

> **Tip**: You can also find the API subscription key in the request headers under `Ocp-Apim-Subscription-Key` if you want to set a manual key in the integration options.

## Devices

Each config entry creates a **device** in HA. Going to **Settings → Devices & Services → SmartCharge** shows a device card per car or station.

- **Car device**: named after the car name you entered during setup. Independent top-level device.
- **SmartCharge hub device**: a single parent device created automatically when you add your first charging station.
- **Station devices**: each station is a child of the SmartCharge hub, named after its static friendly name (e.g. `MVV_station_829151`). Clicking the hub shows all stations underneath it.

> Temporary stations and wallboxes have no associated sensor entities or device card — they are configuration-only entries invisible on the Devices page.

## Entities

### Car entry (6 sensors per car)

See the [Car Tracking](#car-tracking-green-charging) section above.

### EnBW Station entry (1 sensor per station)

- **State**: `available` (at least one charge point is free) or `occupied` (all charge points in use)
- **Dynamic Name**: Updates to show availability, e.g. `2 / 5 - Hauptstraße 10, Stuttgart`. For stations with more than 9 charge points, the available count is spaced (e.g. `1 0 / 10 - StationName`).
- **Icon**: Switches between `mdi:ev-station` and `mdi:ev-station-unavailable`

### Attributes

- `total_charge_points`: Total number of charge points at the station
- `available_count`: Number of currently available charge points
- `occupied_count`: Number of currently occupied charge points
- `latitude` / `longitude`: GPS coordinates (enables map display)
- `address`: Physical address
- **Per charge point** (keyed by EVSE ID): Status, power in kW, and connector type, e.g. `available | 50 kW | CCS`
- `occupancy_weekday`: Average occupancy % by day of week (accumulated over time)
- `occupancy_hourly`: Average occupancy % by hour of day (accumulated over time)

### Reconfiguring entries

| Entry type | Reconfigure | Options (Configure) |
|---|---|---|
| **Car** | Car name, tracker, power sensor, odometer, CO₂ entity, auto-discovery | CO₂ entity, auto-discovery |
| **EnBW Station** | Update interval, friendly name, tariff | Update interval, API key mode, tariff |
| **Wallbox** | Price entity, CO₂ entity | Price entity, CO₂ entity |
| **Temporary Station** | Tariff price, base fee | Tariff price, base fee |

## Dashboard: Occupancy Histograms with Plotly Graph Card

You can visualize the occupancy data as color-coded bar charts using the [Plotly Graph Card](https://github.com/dbuezas/lovelace-plotly-graph-card) (install via HACS → Frontend).

![Occupancy Histogram](docs/occupancy_histogram.png)

```yaml
type: custom:plotly-graph
raw_plotly_config: true
defaults:
  entity:
    type: bar
    showlegend: false
    marker:
      colorscale: Portland
      cmin: 0
      cmax: 100
  xaxes:
    type: category
    showgrid: true
  yaxes:
    range: [0, 100]
    title: Occupancy %
    dtick: 25
    showgrid: true
entities:
  - entity: &station sensor.YOUR_STATION_availability
    name: Hourly
    x: $ex Object.keys(meta.occupancy_hourly || {})
    "y": $ex Object.values(meta.occupancy_hourly || {})
    marker:
      color: $ex Object.values(meta.occupancy_hourly || {})
  - entity: *station
    name: Weekly
    x: $ex Object.keys(meta.occupancy_weekday || {})
    "y": $ex Object.values(meta.occupancy_weekday || {})
    xaxis: x2
    yaxis: y2
    marker:
      color: $ex Object.values(meta.occupancy_weekday || {})
layout:
  title: Station Occupancy
  height: 500
  grid:
    rows: 2
    columns: 1
    subplots: [[xy], [x2y2]]
    roworder: top to bottom
  xaxis:
    dtick: 2
```

> **Note**: Replace `sensor.YOUR_STATION_availability` with your actual station entity ID. The YAML anchor (`&station` / `*station`) ensures the entity is defined only once. The `meta` variable provides direct access to the entity's attributes. Bar colors follow a continuous gradient (Portland colorscale) from low (blue) to high (red) occupancy. Other built-in colorscales: `Jet`, `RdYlGn_r`, `YlOrRd`, `Viridis` — see [Plotly colorscales](https://plotly.com/javascript/colorscales/).

## Service Calls

### Refresh Data

```yaml
service: smartcharge.refresh_data
```

## Automations Example

### Notify when a charge point becomes available

```yaml
automation:
  - alias: "Notify when charging station available"
    trigger:
      platform: state
      entity_id: sensor.my_station_availability
      to: "available"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Charging Station Available"
          message: >
            {{ state_attr('sensor.my_station_availability', 'available_count') }}
            charge point(s) now free!
```

## Troubleshooting

### No entities created

- Check that your station ID is correct on the EnBW map
- Verify internet connectivity
- Review Home Assistant logs for errors (`custom_components.smartcharge`)

### electricityMap API key errors

If you see `electricityMap returned HTTP 401` in the logs, your API key is invalid or expired. Update it via **Settings → Devices & Services → SmartCharge → Reconfigure** (or Configure) on the car entry. The warning is logged once and then suppressed until the key is updated.

### Accumulated stats reset unexpectedly

Energy, CO₂, and cost accumulators are persisted to `.storage/smartcharge.car.<entry_id>` and survive restarts. If values appear to reset, check that the `.storage` folder is writable and not excluded from your backup strategy.

### Data not updating

- Check the update interval setting in the integration options
- Verify the API is accessible
- Restart the integration

## Development

For a local non-Docker approximation of the CI checks, run:

```bash
python scripts/validate_local.py
```

The script validates JSON metadata, checks that `strings.json` and `translations/en.json` stay in sync, and runs `black --check` plus `flake8`.

For community discussions:
- [EnBW Charging Community Thread](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please [open an issue](https://github.com/iandresari/smartcharge/issues).

