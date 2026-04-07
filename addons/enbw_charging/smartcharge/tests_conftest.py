"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def mock_coordinator_data():
    """Return mock coordinator data."""
    return {
        "chargePoints": {
            "171042": {
                "chargePoints": [
                    {
                        "evseId": "DE*RBO*EEEB0258*1001",
                        "status": "Available",
                        "location": {
                            "latitude": 48.7758,
                            "longitude": 9.1829,
                            "address": "Abt. Tor 5",
                        },
                        "powerKw": 11,
                        "connectorType": "TYPE2",
                    },
                    {
                        "evseId": "DE*RBO*EEEB0258*1002",
                        "status": "Occupied",
                        "location": {
                            "latitude": 48.7758,
                            "longitude": 9.1829,
                            "address": "Abt. Tor 5",
                        },
                        "powerKw": 11,
                        "connectorType": "TYPE2",
                    },
                ]
            }
        },
        "occupancyHistory": {},
    }


@pytest.fixture
def mock_config_entry_data():
    """Return mock config entry data."""
    return {
        "charging_stations": [
            {"station_id": "171042", "station_name": "BEG Abt Tor 5"}
        ],
        "update_interval": 300,
    }
