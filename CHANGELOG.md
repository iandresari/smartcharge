# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### Added

- Initial release
- Support for EnBW EV charging stations monitoring
- Real-time charge point status (Available, Occupied, Faulted, Unavailable, Reserved)
- Binary sensors for charge point availability and occupancy
- Occupancy tracking with weekday and hourly statistics
- Dynamic icons based on charge point status
- Location attributes (latitude, longitude, address) for all charge points
- UI configuration flow for easy setup
- Service to add new charging stations dynamically
- Service to remove charging stations
- Manual refresh service for data updates
- Automatic data fetching with configurable update interval
- Support for multiple charging stations
- Type hints throughout codebase
- Comprehensive documentation

### Features

- **Easy Configuration**: Add/remove charging stations via Home Assistant UI
- **Real-time Updates**: Configurable data refresh interval (60s - 60min)
- **Occupancy Analytics**: Track occupancy patterns by weekday and hour
- **Location Data**: GPS coordinates and addresses included in entity attributes
- **Status Icons**: Dynamic icons change based on charge point status
- **Service Calls**: Easy automation with add/remove/refresh services
- **Error Handling**: Graceful handling of API errors and timeouts

## [Unreleased]

### Planned Features

- Token refresh automation
- Price/tariff integration
- Reservation system support
- Energy consumption tracking
- Real-time notification system
- REST API for third-party integration
- Mobile app support
- Calendar-based scheduling
- Historical data export
- Advanced analytics dashboard card

### Known Limitations

- No built-in token refresh (manual management currently)
- No price information available
- No reservation management
