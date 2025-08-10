# Contributing to Confetti 🎉

Thank you for your interest in contributing to Confetti! We welcome contributions from the community and are grateful for any help you can provide.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/confetti.git
   cd confetti
   ```
3. **Add the upstream repository** as a remote:
   ```bash
   git remote add upstream https://github.com/confetti-dev/confetti.git
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv (recommended)
- git

### Installation

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install the package in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=confetti --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### Code Quality Tools

```bash
# Format code with black
black .

# Check code style
black --check .

# Run linter
ruff check .

# Fix linting issues
ruff --fix .

# Type checking
mypy confetti

# Security scan
bandit -r confetti/

# Check dependencies
safety check
```

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to see if the bug has already been reported
2. **Create a new issue** with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - System information (OS, Python version, etc.)
   - Minimal code example

### Suggesting Enhancements

1. **Check existing issues** for similar suggestions
2. **Create a new issue** with:
   - Clear description of the enhancement
   - Use cases and benefits
   - Potential implementation approach
   - Any alternatives considered

### Contributing Code

1. **Find an issue** to work on or create one
2. **Comment on the issue** to let others know you're working on it
3. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** following our coding standards
5. **Write tests** for your changes
6. **Update documentation** as needed
7. **Commit your changes** with descriptive messages
8. **Push to your fork** and create a pull request

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests** and ensure they pass:
   ```bash
   pytest
   ```

3. **Check code quality**:
   ```bash
   black --check .
   ruff check .
   mypy confetti
   ```

4. **Update documentation** if needed

### Pull Request Guidelines

- **Title**: Use a clear, descriptive title
- **Description**: Explain what changes you made and why
- **Link issues**: Reference any related issues
- **Small PRs**: Keep pull requests focused and small
- **Tests**: Include tests for new functionality
- **Documentation**: Update docs for API changes
- **Changelog**: Add entry to CHANGELOG.md for notable changes

### Review Process

1. **Automated checks** will run on your PR
2. **Maintainers will review** your code
3. **Address feedback** promptly
4. **Merge** once approved and checks pass

## Coding Standards

### Python Style Guide

We follow PEP 8 and PEP 257 with these specifications:

- **Line length**: Maximum 79 characters
- **Indentation**: 4 spaces (no tabs)
- **Strings**: Use double quotes
- **Docstrings**: Required for all public modules, functions, classes, and methods
- **Type hints**: Use type hints for function signatures
- **Imports**: Organized with isort (standard library, third-party, local)

### Docstring Format

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    Longer description if needed, explaining what the
    function does in more detail.
    
    Args:
        param1: Description of first parameter.
        param2: Description of second parameter.
        
    Returns:
        Description of return value.
        
    Raises:
        ValueError: When invalid input is provided.
        
    Examples:
        >>> function_name("test", 42)
        True
    """
    pass
```

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line should be 50 characters or less
- Reference issues and pull requests

Example:
```
Add Redis connection pooling support

- Implement connection pool manager
- Add configuration for pool size
- Update documentation with examples

Fixes #123
```

## Testing Guidelines

### Test Structure

```python
"""Test module docstring."""

import pytest
from confetti import SomeClass


class TestSomeClass:
    """Test suite for SomeClass."""
    
    def test_initialization(self):
        """Test that SomeClass initializes correctly."""
        obj = SomeClass()
        assert obj is not None
    
    def test_method_with_valid_input(self):
        """Test method with valid input."""
        obj = SomeClass()
        result = obj.method("valid")
        assert result == "expected"
    
    def test_method_with_invalid_input(self):
        """Test that method raises error with invalid input."""
        obj = SomeClass()
        with pytest.raises(ValueError, match="Invalid input"):
            obj.method("invalid")
```

### Test Coverage

- Aim for at least 90% code coverage
- Test edge cases and error conditions
- Include integration tests for complex features
- Mock external dependencies appropriately

## Documentation

### Code Documentation

- All public APIs must have docstrings
- Include examples in docstrings when helpful
- Keep documentation up-to-date with code changes

### User Documentation

- Update README.md for new features
- Add examples to the examples/ directory
- Update API reference documentation
- Consider writing a tutorial for complex features

### Building Documentation

```bash
cd docs
make html
open _build/html/index.html
```

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality
- PATCH version for backwards-compatible bug fixes

### Release Checklist

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Build and check distribution:
   ```bash
   python -m build
   twine check dist/*
   ```
5. Create git tag:
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```
6. GitHub Actions will automatically publish to PyPI

## Getting Help

- **Discord**: Join our [Discord server](https://discord.gg/confetti)
- **Discussions**: Use [GitHub Discussions](https://github.com/confetti-dev/confetti/discussions)
- **Issues**: Report bugs via [GitHub Issues](https://github.com/confetti-dev/confetti/issues)

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Confetti! 🎊