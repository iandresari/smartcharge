# SmartCharge - EV Charging Station Monitor

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=iandresari&repository=smartcharge&category=integration)

A Home Assistant integration for monitoring EnBW electric vehicle charging stations in Germany.

## Features

- **Easy Configuration**: Search nearby stations on a map or enter a station ID directly — one config entry per station
- **Real-time Status**: One sensor per charge point showing live status (available, occupied, faulted, etc.)
- **Occupancy Tracking**: Persistent occupancy histograms by hour-of-day and weekday, accumulating over time and surviving restarts
- **Map Integration**: Device tracker entity places each station on the HA map with GPS coordinates
- **Location Data**: GPS coordinates and address as attributes on each charge point sensor

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
4. Choose **Search Nearby Stations** (recommended) to find stations on a map, or enter a station ID manually
5. If searching: drag the map pin to your area, adjust the radius, then pick a station from the results
6. Select which charge points to monitor
7. Configure the update interval (60–3600 seconds, default 300)

To monitor multiple stations, add the integration once per station.

## Getting Station IDs (Manual Fallback)

If you prefer to enter a station ID directly, you can find it using your browser's developer tools:

1. Open the [EnBW charging map](https://www.enbw.com/elektromobilitaet/produkte/mobilityplus-app/ladestation-finden/map)
2. Open your browser's developer tools:
   - **Chrome**: Press `F12` or `Ctrl+Shift+I`, then go to the **Network** tab
   - **Firefox**: Press `F12` or `Ctrl+Shift+I`, then go to the **Network** tab
3. Click on a charging station on the map
4. In the Network tab, look for a request to the EnBW API, e.g.:
   ```
   https://enbw-emp.azure-api.net/emobility-public-api/api/v1/chargestations/134057
   ```
5. The number at the end of the URL (e.g. `134057`) is the **station ID**

> **Tip**: You can also find the API subscription key in the request headers under `Ocp-Apim-Subscription-Key` if you want to set a manual key in the integration options.

## Entities

Each config entry (one per station) creates:

### Sensors

- **Charge Point Status** (one per charge point): Current status — `available`, `occupied`, `faulted`, `unavailable`, or `reserved`
- **Station Occupancy**: Overall occupancy percentage for the station

### Attributes

Charge point status sensors include:
- `evse_id`: Unique EVSE identifier
- `status`: Raw status from API
- `latitude` / `longitude`: GPS coordinates
- `address`: Physical address
- `power`: Charging power in kW
- `connector_type`: Connector type

Occupancy sensor includes:
- `occupancy_weekday`: Average occupancy % by day of week (accumulated over time)
- `occupancy_hourly`: Average occupancy % by hour of day (accumulated over time)

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
  - entity: &station sensor.YOUR_STATION_occupancy
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

> **Note**: Replace `sensor.YOUR_STATION_occupancy` with your actual occupancy entity ID. The YAML anchor (`&station` / `*station`) ensures the entity is defined only once. The `meta` variable provides direct access to the entity's attributes. Bar colors follow a continuous gradient (Portland colorscale) from low (blue) to high (red) occupancy. Other built-in colorscales: `Jet`, `RdYlGn_r`, `YlOrRd`, `Viridis` — see [Plotly colorscales](https://plotly.com/javascript/colorscales/).

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
      entity_id: sensor.my_station_charger_1
      to: "available"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Charging Station Available"
          message: "Charger 1 is now available!"
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
