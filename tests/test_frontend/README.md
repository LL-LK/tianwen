# Tianwen-AGI Frontend Playwright Tests

Playwright-based integration tests for the Tianwen-AGI frontend interface.

## Test Structure

```
tests/test_frontend/
├── __init__.py              # Package initialization
├── conftest.py              # Playwright configuration and fixtures
├── pytest.ini               # Pytest configuration
├── test_navigation.py       # Tab navigation and header tests
├── test_harness_tab.py      # Harness Tab (PGE Loop) tests
├── test_benchmark_tab.py    # Benchmark Tab tests
├── test_skills_tab.py       # Skills Tab tests
└── test_astronomy_tab.py    # Astronomy Tab tests
```

## Installation

```bash
# Install Playwright and pytest plugin
pip install pytest pytest-playwright

# Install Chromium browser
playwright install chromium
```

## Running Tests

```bash
# Run all frontend tests
pytest tests/test_frontend/ -v

# Run with headless mode (default)
pytest tests/test_frontend/ -v --headed=false

# Run specific test file
pytest tests/test_frontend/test_harness_tab.py -v

# Run tests matching a pattern
pytest tests/test_frontend/ -v -k "harness"
```

## Test Coverage

### Navigation Tests (`test_navigation.py`)
- Page loading
- Tab navigation bar existence
- All main tabs presence
- Tab switching functionality
- Default tab behavior
- Keyboard shortcuts

### Harness Tab Tests (`test_harness_tab.py`)
- Tab activation
- PGE Loop visualization
- Plan/Generate/Evaluate/Iterate nodes
- Component registry
- Stat items display
- Four phases display

### Benchmark Tab Tests (`test_benchmark_tab.py`)
- Tab activation
- Benchmark selector
- Configuration preview
- Run/Refresh buttons
- YAML configuration example
- Benchmark level options

### Skills Tab Tests (`test_skills_tab.py`)
- Tab activation
- Skill registry list
- Search functionality
- Category cards (Astronomy, Agent, Grading, Tools)
- Refresh functionality

### Astronomy Tab Tests (`test_astronomy_tab.py`)
- Tab activation
- FITS Protocol section
- Time-Domain Protocol section
- Photometry Protocol section
- Coordinate Protocol section
- CI/CD integration status

## Configuration

The tests are configured to run against the production frontend URL by default.
You can modify `conftest.py` to use a local development server.

## Headless Mode

Tests are designed to run in headless mode by default. To run with a visible browser:

```python
# In conftest.py, set:
playwright_headless = false
```

Or use the `--headed` flag with pytest-playwright.
