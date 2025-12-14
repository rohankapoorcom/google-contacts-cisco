# google-contacts-cisco

## Setup

This project uses a devcontainer for development. The devcontainer will automatically:
- Set up a Python 3.13 environment
- Install all project dependencies (including dev dependencies)
- Configure VS Code/Cursor with Python extensions

### Using the Devcontainer

1. Open the project in VS Code or Cursor
2. When prompted, click "Reopen in Container" (or use Command Palette: "Dev Containers: Reopen in Container")
3. The container will build and install dependencies automatically

The devcontainer includes:
- Python 3.11
- Black formatter
- Pytest testing framework
- Mypy type checker
- All VS Code/Cursor Python extensions pre-configured

## Development

### Code Formatting
Format code with black:
```bash
black .
```

### Type Checking
Run mypy:
```bash
mypy .
```

### Testing
Run tests with pytest:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=google_contacts_cisco --cov-report=html
```

