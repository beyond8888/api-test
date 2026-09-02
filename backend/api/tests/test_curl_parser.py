"""Tests for the curl parser."""
import pytest

from api.curl_parser.exceptions import NotACurlCommand
from api.curl_parser.parser import CurlParser


class TestBasicCurlParsing:
    def test_simple_get(self):
        result = CurlParser("curl https://example.com/api").parse()
        assert result["method"] == "GET"
        assert result["url"] == "https://example.com/api"
        assert result["base_url"] == "https://example.com"

    def test_post_with_data(self):
        curl = """curl -X POST https://api.example.com/users \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer abc123' \\
  --data-raw '{"name":"John","age":30}'"""
        result = CurlParser(curl).parse()
        assert result["method"] == "POST"
        assert result["url"] == "https://api.example.com/users"
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["Authorization"] == "Bearer abc123"
        assert result["body"] == {"name": "John", "age": 30}
        assert result["body_type"] == "json"
        assert result["auth"]["type"] == "bearer"
        assert result["auth"]["token"] == "abc123"

    def test_put_request(self):
        result = CurlParser("curl -X PUT https://api.example.com/item/1").parse()
        assert result["method"] == "PUT"

    def test_delete_request(self):
        result = CurlParser("curl -X DELETE https://api.example.com/item/1").parse()
        assert result["method"] == "DELETE"

    def test_no_method_defaults_to_get(self):
        result = CurlParser("curl https://example.com").parse()
        assert result["method"] == "GET"

    def test_data_triggers_post(self):
        result = CurlParser("curl https://example.com -d 'key=value'").parse()
        assert result["method"] == "POST"


class TestHeaderParsing:
    def test_single_header(self):
        result = CurlParser("curl -H 'X-Custom: value' https://example.com").parse()
        assert result["headers"]["X-Custom"] == "value"

    def test_multiple_headers(self):
        curl = """curl https://example.com \\
  -H 'Accept: application/json' \\
  -H 'X-API-Key: secret'"""
        result = CurlParser(curl).parse()
        assert result["headers"]["Accept"] == "application/json"
        assert result["headers"]["X-API-Key"] == "secret"

    def test_long_header_flag(self):
        result = CurlParser("curl --header 'X-Foo: bar' https://example.com").parse()
        assert result["headers"]["X-Foo"] == "bar"


class TestCookieParsing:
    def test_cookie_flag(self):
        result = CurlParser("curl -b 'session=abc123; token=xyz' https://example.com").parse()
        assert result["cookies"]["session"] == "abc123"
        assert result["cookies"]["token"] == "xyz"

    def test_long_cookie_flag(self):
        result = CurlParser("curl --cookie 'a=1' https://example.com").parse()
        assert result["cookies"]["a"] == "1"


class TestFormData:
    def test_form_field(self):
        result = CurlParser("curl -F 'name=John' -F 'age=30' https://example.com").parse()
        assert result["body_type"] == "multipart"
        assert result["body"]["name"] == "John"
        assert result["body"]["age"] == "30"


class TestAuthParsing:
    def test_bearer_auth_from_header(self):
        result = CurlParser("curl -H 'Authorization: Bearer token123' https://example.com").parse()
        assert result["auth"]["type"] == "bearer"
        assert result["auth"]["token"] == "token123"

    def test_basic_auth_from_header(self):
        result = CurlParser("curl -H 'Authorization: Basic dXNlcjpwYXNz' https://example.com").parse()
        assert result["auth"]["type"] == "basic"

    def test_user_flag(self):
        result = CurlParser("curl -u 'admin:secret' https://example.com").parse()
        auth_header = result["headers"].get("Authorization", "")
        assert auth_header.startswith("Basic ")
        assert "Detected -u flag" in result["warnings"][0]


class TestBooleanFlags:
    def test_insecure(self):
        result = CurlParser("curl -k https://example.com").parse()
        assert result["insecure"] is True

    def test_compressed(self):
        result = CurlParser("curl --compressed https://example.com").parse()
        assert result["compressed"] is True

    def test_silent(self):
        result = CurlParser("curl -s https://example.com").parse()
        assert result["warnings"] == []

    def test_combined_flags(self):
        result = CurlParser("curl -sSL https://example.com").parse()
        assert result["warnings"] == []


class TestErrorHandling:
    def test_empty_input(self):
        with pytest.raises(NotACurlCommand):
            CurlParser("").parse()

    def test_non_curl_command(self):
        with pytest.raises(NotACurlCommand):
            CurlParser("wget https://example.com").parse()

    def test_non_curl_start(self):
        with pytest.raises(NotACurlCommand):
            CurlParser("echo hello").parse()


class TestTerminalArtifacts:
    def test_dollar_prompt(self):
        result = CurlParser("$ curl https://example.com").parse()
        assert result["url"] == "https://example.com"

    def test_angle_prompt(self):
        result = CurlParser("> curl https://example.com").parse()
        assert result["url"] == "https://example.com"


class TestPostmanVariableUrls:
    """Postman/Insomnia export URLs use {{variable}} placeholders and lack a scheme."""

    def test_variable_url_with_path(self):
        curl = (
            "curl --location -g --request POST "
            "'{{baseUrl}}/lgi-capacity/ai-audit/v2/callback' "
            "--header 'X-App-ID: lgi_capacity_fc32d522' "
            "--header 'Authorization: {{Authentication}}' "
            "--header 'Content-Type: application/json; charset=utf-8' "
            "--data-raw '{\"code\": 0, \"message\": \"success\"}'"
        )
        result = CurlParser(curl).parse()
        assert result["method"] == "POST"
        assert result["url"] == "{{baseUrl}}/lgi-capacity/ai-audit/v2/callback"
        assert result["headers"]["X-App-ID"] == "lgi_capacity_fc32d522"
        assert result["headers"]["Authorization"] == "{{Authentication}}"
        assert result["body_type"] == "json"
        # No spurious warnings from -g / --location / --request
        assert result["warnings"] == []

    def test_variable_url_without_path(self):
        result = CurlParser("curl '{{baseUrl}}' -X GET").parse()
        assert result["url"] == "{{baseUrl}}"
        assert result["warnings"] == []

    def test_globoff_flag_is_recognized(self):
        result = CurlParser("curl -g '{{baseUrl}}/x'").parse()
        assert result["url"] == "{{baseUrl}}/x"
        assert result["warnings"] == []

    def test_path_only_url(self):
        result = CurlParser("curl -X POST '/internal/api' -H 'X-Foo: bar'").parse()
        assert result["url"] == "/internal/api"
        assert result["warnings"] == []
