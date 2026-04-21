# Contributing to unoconv-api

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/unoconv-api.git
cd unoconv-api

# Install dependencies
pip install -r api/requirements.txt

# Install system dependencies
sudo apt-get install -y imagemagick ffmpeg libreoffice unoconv ghostscript poppler-utils

# Run development server
cd api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Code Style

- Follow PEP 8
- Use type hints
- Max line length: 100 characters

## Testing

```bash
pytest api/tests/ -v
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest api/tests/ -v`
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

## Release Process

1. Update version in relevant files
2. Create git tag: `git tag v1.0.0`
3. Push tag: `git push origin v1.0.0`
4. GitHub Actions will build and release automatically