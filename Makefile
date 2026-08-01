.PHONY: help install test run clean lint demo

# Default target
help:
	@echo "CLI File Organizer - Makefile Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make install    - Install the package in development mode"
	@echo "  make test       - Run the test suite"
	@echo "  make run        - Run the organizer on current directory (dry-run)"
	@echo "  make clean      - Remove Python cache files and build artifacts"
	@echo "  make lint       - Check code quality (requires flake8)"
	@echo "  make demo       - Run a demo on a sample folder"
	@echo ""

# Install package in development mode
install:
	@echo "Installing package in development mode..."
	pip install -e .
	@echo "✓ Installed! You can now use 'file-organizer' command"

# Run tests
test:
	@echo "Running tests..."
	python -m pytest test_organizer.py -v

# Run organizer on current directory (dry-run mode)
run:
	@echo "Running organizer on current directory (dry-run)..."
	python organizer.py . --dry-run

# Clean up cache and build files
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/
	@echo "✓ Cleaned!"

# Lint code (requires flake8)
lint:
	@echo "Running linter..."
	@command -v flake8 >/dev/null 2>&1 || { echo "flake8 not installed. Run: pip install flake8"; exit 1; }
	flake8 organizer.py test_organizer.py --max-line-length=100 --ignore=E501,W503
	@echo "✓ Linting passed!"

# Demo with sample files
demo:
	@echo "Creating demo folder..."
	@mkdir -p /tmp/demo_organizer
	@touch /tmp/demo_organizer/{photo.jpg,report.pdf,song.mp3,video.mp4,archive.zip,app.py,data.json,README.md}
	@echo ""
	@echo "Running organizer on demo folder..."
	python organizer.py /tmp/demo_organizer --dry-run
	@echo ""
	@echo "To actually organize, run:"
	@echo "  python organizer.py /tmp/demo_organizer"
