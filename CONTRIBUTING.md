# CONTRIBUTING Guidelines

## Development Setup

### Prerequisites
- Python 3.9+
- Home Assistant development environment
- Git

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/your-repo/enbw-charging
cd enbw-charging

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install Home Assistant in dev mode
git clone https://github.com/home-assistant/core core
cd core
pip install -e .
```

## Code Style

### Formatting
- Use `black` for code formatting
- Use `flake8` for linting
- Use `isort` for import sorting
- Use `mypy` for type checking

```bash
# Format code
black enbw_charging/

# Lint
flake8 enbw_charging/

# Sort imports
isort enbw_charging/

# Type check
mypy enbw_charging/
```

### Python Version
- Minimum Python 3.9
- Use type hints for all functions
- Follow Google-style docstrings

## Testing

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_config_flow.py

# Coverage report
pytest --cov=enbw_charging tests/
```

### Local Validation

Before pushing, run the local validator to cover the non-Docker checks used in this repository:

```bash
python scripts/validate_local.py
```

This validates JSON files, checks translation key parity, and runs Black plus flake8.

### Test Structure
```
tests/
├── conftest.py              # Shared fixtures
├── test_config_flow.py      # Config flow tests
├── test_coordinator.py      # Data coordinator tests
├── test_sensor.py           # Sensor tests
└── test_binary_sensor.py    # Binary sensor tests
```

## API Integration Notes

### Endpoints
- Base: `https://enbw-emp.azure-api.net/emobility-public-api/api/v1`
- Charging Stations: `/chargestations/{stationId}`

### Headers Required
```python
headers = {
    "User-Agent": "Home Assistant",
    "Ocp-Apim-Subscription-Key": "YOUR_KEY",
    "Referer": "https://www.enbw.com/",
    "Origin": "https://www.enbw.com",
}
```

### Authentication
- Uses API subscription key
- Included in request headers
- No OAuth/token refresh (currently)

## Adding Features

### Adding a New Entity Type

1. Create new file: `entity_type.py`
2. Extend `CoordinatorEntity` and appropriate base class
3. Implement required properties:
   - `_attr_unique_id`
   - `_attr_name`
   - `native_value` (for sensors)
   - `is_on` (for binary sensors)
4. Update `async_setup_entry()` in `__init__.py`
5. Add tests in `tests/test_entity_type.py`
6. Update manifest.json if needed

### Adding a New Service

1. Add service definition to `services.py`
2. Register in `async_setup_services()`
3. Add tests for service functionality
4. Document in README.md

## Debugging

### Enable Debug Logging
```yaml
logger:
  logs:
    enbw_charging: debug
```

### Common Issues

**No entities created**
- Check station ID is valid
- Verify API connectivity
- Check logs for HTTP errors

**Data not updating**
- Check update interval setting
- Verify API returns data
- Check for coordinator errors

**Timeout errors**
- Check network connectivity
- Verify API is responsive
- Increase timeout in code if needed

## Submission Guidelines

### Before Submitting PR
- [ ] Code formatted with `black`
- [ ] Tests added/updated
- [ ] Type hints added
- [ ] Documentation updated
- [ ] Docstrings written
- [ ] No hardcoded credentials
- [ ] Proper error handling

### PR Descriptions
Include:
- What problem does it solve?
- How does it work?
- Breaking changes?
- Tested scenarios

### Commit Messages
Follow conventional commits:
```
feat: Add new charge point reservation feature
fix: Handle API timeout gracefully
docs: Update installation instructions
refactor: Simplify occupancy calculation
test: Add coordinator tests
```

## Documentation Updates

### Files to Update
- `README.md` - User-facing documentation
- `ARCHITECTURE.md` - Technical details  
- `CONFIGURATION.md` - Configuration examples
- Docstrings in code (Google style)

### Documentation Style
- Clear and concise
- Include examples
- Keep updated with code changes

## Release Process

1. Update version in `manifest.json`
2. Update `CHANGELOG.md`
3. Create git tag
4. Push to repository
5. Create GitHub release

## Community

- [Home Assistant Community Forum](https://community.home-assistant.io/)
- [EnBW Charging Discussion](https://community.home-assistant.io/t/status-of-enbw-charging-stations/409573)

## License

All contributions are subject to the MIT license.
