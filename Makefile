.PHONY: help install dev run clean test lint format build

# Default target - show help
help:
	@echo "NeoZen - Available Make Commands"
	@echo "================================="
	@echo ""
	@echo "  make install    - Install NeoZen in a virtual environment"
	@echo "  make dev        - Install with development dependencies"
	@echo "  make run        - Run NeoZen"
	@echo "  make clean      - Remove build artifacts and virtual environment"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting checks"
	@echo "  make format     - Format code with black"
	@echo "  make build      - Build standalone executable with PyInstaller"
	@echo ""

# Install NeoZen in production mode
install:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Installing NeoZen..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -e .
	@echo ""
	@echo "✓ Installation complete!"
	@echo "Run 'make run' or 'source venv/bin/activate && neozen'"

# Install with development dependencies
dev:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Installing NeoZen with dev dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -e ".[dev]"
	@echo ""
	@echo "✓ Development environment ready!"

# Run NeoZen
run:
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	./venv/bin/neozen

# Clean build artifacts and virtual environment
clean:
	@echo "Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf venv/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleanup complete!"

# Run tests
test:
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Run 'make dev' first."; \
		exit 1; \
	fi
	./venv/bin/pytest tests/ -v

# Run linting
lint:
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Run 'make dev' first."; \
		exit 1; \
	fi
	@echo "Running ruff..."
	./venv/bin/ruff check .
	@echo "✓ Linting complete!"

# Format code
format:
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Run 'make dev' first."; \
		exit 1; \
	fi
	@echo "Formatting code with black..."
	./venv/bin/black .
	@echo "✓ Formatting complete!"

# Build standalone executable
build:
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Installing build dependencies..."
	./venv/bin/pip install -e ".[build]"
	@echo "Building executable with PyInstaller..."
	./venv/bin/pyinstaller --clean --noconfirm neozen.spec
	@echo "Moving executable to project directory..."
	@if [ -f dist/neozen ]; then \
		mv dist/neozen ./neozen-linux || mv dist/neozen ./neozen-macos; \
	elif [ -f dist/neozen.exe ]; then \
		mv dist/neozen.exe ./neozen.exe; \
	fi
	@echo "Cleaning up build directories..."
	rm -rf build/ dist/ *.spec~
	@echo ""
	@echo "✓ Build complete!"
	@if [ -f neozen-linux ]; then \
		echo "  Executable: ./neozen-linux"; \
	elif [ -f neozen-macos ]; then \
		echo "  Executable: ./neozen-macos"; \
	elif [ -f neozen.exe ]; then \
		echo "  Executable: ./neozen.exe"; \
	fi
