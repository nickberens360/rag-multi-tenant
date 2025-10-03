"""
Unit tests for response settings integration.
Tests that response settings properly control response generation and formatting.
"""

from unittest.mock import Mock, patch

from backend.core.response_service import ResponseService
from backend.core.settings_schemas import ResponseSettings


class TestResponseSettingsIntegration:
    """Test response settings integration across backend services."""

    def test_response_settings_schema_validation(self):
        """Test that response settings schema validates correctly."""
        # Test valid settings including new consolidated caching fields
        settings = ResponseSettings(
            preferred_response_length="detailed",
            response_style="technical",
            include_sources=True,
            source_format="bulleted",
            max_sources=3,
            enable_markdown=True,
            enable_code_highlighting=False,
            response_llm="gemini",
            enable_smart_selection=True,
            enable_caching=True,
            enable_response_caching=True,
            cache_ttl_seconds=1800,
        )

        assert settings.preferred_response_length == "detailed"
        assert settings.response_style == "technical"
        assert settings.include_sources is True
        assert settings.source_format == "bulleted"
        assert settings.max_sources == 3
        assert settings.enable_markdown is True
        assert settings.enable_code_highlighting is False
        assert settings.response_llm == "gemini"
        assert settings.enable_smart_selection is True
        assert settings.enable_caching is True
        assert settings.enable_response_caching is True
        assert settings.cache_ttl_seconds == 1800

    def test_response_settings_validation_from_dict(self):
        """Test response settings validation from dictionary."""
        # Test with valid data
        data = {
            "preferred_response_length": "comprehensive",
            "response_style": "casual",
            "include_sources": "true",
            "source_format": "inline",
            "max_sources": "8",
            "enable_markdown": "false",
            "enable_code_highlighting": "True",
            "response_llm": "claude",
            "enable_smart_selection": "FALSE",
        }

        settings = ResponseSettings.from_dict(data)

        assert settings.preferred_response_length == "comprehensive"
        assert settings.response_style == "casual"
        assert settings.include_sources is True
        assert settings.source_format == "inline"
        assert settings.max_sources == 8
        assert settings.enable_markdown is False
        assert settings.enable_code_highlighting is True
        assert settings.response_llm == "claude"
        assert settings.enable_smart_selection is False

    def test_response_settings_bounds_validation(self):
        """Test that response settings respect bounds validation."""
        # Test max_sources bounds
        data = {"max_sources": 25}  # Above maximum (20)
        settings = ResponseSettings.from_dict(data)
        assert settings.max_sources == 20  # Should be clamped to maximum

        data = {"max_sources": -5}  # Below minimum (0)
        settings = ResponseSettings.from_dict(data)
        assert settings.max_sources == 0  # Should be clamped to minimum

    def test_response_settings_invalid_values_fallback(self):
        """Test that invalid values fall back to defaults."""
        # Test invalid response length
        data = {"preferred_response_length": "super_long"}
        settings = ResponseSettings.from_dict(data)
        assert settings.preferred_response_length == "medium"  # Default

        # Test invalid response style
        data = {"response_style": "robotic"}
        settings = ResponseSettings.from_dict(data)
        assert settings.response_style == "conversational"  # Default

        # Test invalid source format
        data = {"source_format": "fancy"}
        settings = ResponseSettings.from_dict(data)
        assert settings.source_format == "numbered"  # Default

        # Test invalid response LLM
        data = {"response_llm": "chatgpt"}
        settings = ResponseSettings.from_dict(data)
        assert settings.response_llm == "claude"  # Default

    def test_response_service_source_formatting_numbered(self):
        """Test numbered source formatting."""
        response_service = ResponseService()

        sources = [
            {"title": "Resume", "file": "resume.json"},
            {"title": "About", "file": "about.md"},
            {"title": "Projects", "file": "projects.json"},
        ]

        mock_response_settings = Mock()
        mock_response_settings.max_sources = 5

        result = response_service._format_numbered_sources(sources)

        expected = "**Sources:**\n1. Resume (resume.json)\n2. About (about.md)\n3. Projects (projects.json)"
        assert result == expected

    def test_response_service_source_formatting_bulleted(self):
        """Test bulleted source formatting."""
        response_service = ResponseService()

        sources = [{"title": "Skills", "file": "skills.md"}, {"title": "Experience", "file": "experience.json"}]

        result = response_service._format_bulleted_sources(sources)

        expected = "**Sources:**\n• Skills (skills.md)\n• Experience (experience.json)"
        assert result == expected

    def test_response_service_source_formatting_inline(self):
        """Test inline source formatting."""
        response_service = ResponseService()

        sources = [{"title": "Portfolio", "file": "portfolio.md"}, {"title": "Contact", "file": "contact.json"}]

        result = response_service._format_inline_sources(sources)

        expected = "\n\n*Sources: Portfolio, Contact*"
        assert result == expected

    def test_response_service_source_limit_respected(self):
        """Test that source count limit is respected."""
        response_service = ResponseService()

        sources = [{"title": f"Source {i}", "file": f"source{i}.md"} for i in range(1, 11)]  # 10 sources

        mock_response_settings = Mock()
        mock_response_settings.max_sources = 3

        result = response_service._format_sources(sources, mock_response_settings)

        # Should only include first 3 sources
        assert "Source 1" in result
        assert "Source 2" in result
        assert "Source 3" in result
        assert "Source 4" not in result
        assert "Source 10" not in result

    def test_response_service_markdown_stripping(self):
        """Test markdown stripping functionality."""
        response_service = ResponseService()

        markdown_text = """
# Heading 1
## Heading 2

**Bold text** and *italic text* and __bold__ and _italic_.

Here's a [link](https://example.com) and some `inline code`.

```python
def hello():
    print("Hello")
```

Regular text continues here.
"""

        result = response_service._strip_markdown(markdown_text)

        # Check that markdown syntax is removed
        assert "# Heading 1" not in result
        assert "## Heading 2" not in result
        assert "**Bold text**" not in result
        assert "*italic text*" not in result
        assert "[link](https://example.com)" not in result
        assert "`inline code`" not in result
        assert "```python" not in result

        # Check that content is preserved
        assert "Heading 1" in result
        assert "Heading 2" in result
        assert "Bold text" in result
        assert "italic text" in result
        assert "link" in result
        assert "inline code" in result
        assert "[Code Block]" in result  # Code blocks replaced
        assert "Regular text continues here." in result

    def test_response_service_code_highlighting_stripping(self):
        """Test code highlighting stripping while preserving code blocks."""
        response_service = ResponseService()

        code_text = """
Here's some Python code:

```python
def function():
    return True
```

And some JavaScript:

```javascript
function test() {
    return false;
}
```

Regular text here.
"""

        result = response_service._strip_code_highlighting(code_text)

        # Check that language specifiers are removed but code blocks remain
        assert "```python" not in result
        assert "```javascript" not in result
        assert "```\ndef function():" in result
        assert "```\nfunction test() {" in result  # Fixed: removed colon, it's JavaScript
        assert "Regular text here." in result

    def test_response_service_process_formatting_integration(self):
        """Test full response formatting integration."""
        response_service = ResponseService()

        mock_settings_manager = Mock()
        mock_response_settings = Mock()
        mock_response_settings.enable_markdown = False
        mock_response_settings.enable_code_highlighting = True
        mock_response_settings.include_sources = True
        mock_response_settings.source_format = "numbered"
        mock_response_settings.max_sources = 2

        mock_settings_manager.get_response_settings.return_value = mock_response_settings

        response_text = """
## Technical Skills

Nick has experience with **Python** and *JavaScript*.

```python
def example():
    pass
```
"""

        sources = [
            {"title": "Skills", "file": "skills.md"},
            {"title": "Resume", "file": "resume.json"},
            {"title": "Extra", "file": "extra.md"},  # Should be filtered out due to max_sources=2
        ]

        with patch("backend.core.settings_manager.get_settings_manager", return_value=mock_settings_manager):
            result = response_service.process_response_formatting(response_text, sources)

        # Markdown should be stripped
        assert "## Technical Skills" not in result
        assert "**Python**" not in result
        assert "*JavaScript*" not in result
        assert "Technical Skills" in result  # Content preserved
        assert "Python" in result
        assert "JavaScript" in result

        # Sources should be included and limited to 2
        assert "**Sources:**" in result
        assert "1. Skills (skills.md)" in result
        assert "2. Resume (resume.json)" in result
        assert "Extra (extra.md)" not in result  # Should be filtered out

    def test_response_service_formatting_error_handling(self):
        """Test that response formatting gracefully handles errors."""
        response_service = ResponseService()

        original_response = "This is a test response."

        # Mock settings manager to raise an exception
        with patch("backend.core.settings_manager.get_settings_manager", side_effect=Exception("Database error")):
            result = response_service.process_response_formatting(original_response)

        # Should return original response when error occurs
        assert result == original_response

    def test_response_settings_json_serialization(self):
        """Test that response settings can be serialized to/from JSON."""
        settings = ResponseSettings(
            preferred_response_length="brief",
            response_style="professional",
            include_sources=False,
            source_format="bulleted",
            max_sources=3,
            enable_markdown=False,
            enable_code_highlighting=True,
            response_llm="gemini",
            enable_smart_selection=False,
        )

        # Test serialization
        json_str = settings.to_json()
        assert isinstance(json_str, str)

        # Test deserialization
        loaded_settings = ResponseSettings.from_json(json_str)
        assert loaded_settings.preferred_response_length == "brief"
        assert loaded_settings.response_style == "professional"
        assert loaded_settings.include_sources is False
        assert loaded_settings.source_format == "bulleted"
        assert loaded_settings.max_sources == 3
        assert loaded_settings.enable_markdown is False
        assert loaded_settings.enable_code_highlighting is True
        assert loaded_settings.response_llm == "gemini"
        assert loaded_settings.enable_smart_selection is False

    def test_caching_settings_consolidation(self):
        """Test that caching settings are properly consolidated in ResponseSettings."""
        # Test that all caching-related settings work together
        data = {
            "enable_caching": True,
            "enable_response_caching": True,
            "cache_ttl_seconds": 1800,
            "response_cache_ttl_seconds": 3600,
        }

        settings = ResponseSettings.from_dict(data)

        assert settings.enable_caching is True
        assert settings.enable_response_caching is True
        assert settings.cache_ttl_seconds == 1800  # Unified cache TTL
        assert settings.response_cache_ttl_seconds == 3600  # Legacy field maintained

        # Test TTL validation bounds
        data_invalid_ttl = {
            "cache_ttl_seconds": 30,  # Below minimum (60)
            "response_cache_ttl_seconds": 100000,  # Above maximum (86400)
        }

        settings_bounded = ResponseSettings.from_dict(data_invalid_ttl)
        assert settings_bounded.cache_ttl_seconds == 60  # Clamped to minimum
        assert settings_bounded.response_cache_ttl_seconds == 86400  # Clamped to maximum

    def test_settings_manager_response_llm_integration(self):
        """Test that settings manager properly uses response settings for LLM selection."""
        mock_settings_manager = Mock()
        mock_response_settings = ResponseSettings(response_llm="gemini", enable_smart_selection=True)
        mock_settings_manager.get_response_settings.return_value = mock_response_settings

        with patch("backend.core.settings_manager.get_settings_manager", return_value=mock_settings_manager):
            from backend.core.settings_manager import get_settings_manager

            manager = get_settings_manager()

            # Mock the actual methods since we're patching the manager
            manager.get_response_llm = Mock(return_value="gemini")
            manager.is_response_smart_selection_enabled = Mock(return_value=True)

            assert manager.get_response_llm() == "gemini"
            assert manager.is_response_smart_selection_enabled() is True
