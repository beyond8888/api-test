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


class TestExplicitUrlFlag:
    """`curl --url 'https://...'` — the explicit URL option form emitted by
    browsers / proxy recorders. Previously the URL token was silently dropped,
    leaving the imported request with an empty URL."""

    def test_url_option_space_form(self):
        curl = (
            "curl --url 'https://4u2.wanlianyida.com/gateway/lmt-platform/car/audit-submit' "
            "-H 'content-type: application/json;charset=UTF-8' "
            "--data-raw '{\"api_version\":\"1.0.0\"}'"
        )
        result = CurlParser(curl).parse()
        assert result["method"] == "POST"
        assert result["url"] == "https://4u2.wanlianyida.com/gateway/lmt-platform/car/audit-submit"
        assert result["body_type"] == "json"
        assert result["warnings"] == []

    def test_url_option_equals_form(self):
        result = CurlParser("curl --url=https://example.com/api -X POST").parse()
        assert result["method"] == "POST"
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []

    def test_url_option_full_command_shape(self):
        curl = (
            "curl --url 'https://4u2.wanlianyida.com/gateway/lmt-platform/car/audit-submit' \\\n"
            "  -H 'accept: application/json' \\\n"
            "  -H 'authorization: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ7fSJ9' \\\n"
            "  -H 'content-type: application/json;charset=UTF-8' \\\n"
            "  -b '_abfpc=abc123; cna=def456' \\\n"
            "  --data-raw '{\"plateNo\":\"晋K88680\",\"id\":\"2092483221332234240\"}'"
        )
        result = CurlParser(curl).parse()
        assert result["method"] == "POST"
        assert result["url"] == "https://4u2.wanlianyida.com/gateway/lmt-platform/car/audit-submit"
        assert result["headers"]["accept"] == "application/json"
        assert result["headers"]["authorization"].startswith("eyJhbGciOiJIUzI1NiJ9")
        assert result["cookies"]["_abfpc"] == "abc123"
        assert result["cookies"]["cna"] == "def456"
        assert result["body_type"] == "json"
        assert result["body"]["plateNo"] == "晋K88680"
        assert result["warnings"] == []

    def test_positional_url_still_works_after_url_flag(self):
        # curl runs the command once per URL; only the first is supported here,
        # the extra positional URL is reported instead of silently winning.
        result = CurlParser("curl --url 'https://a.com/x' https://b.com/y").parse()
        assert result["url"] == "https://a.com/x"
        assert len(result["warnings"]) == 1
        assert "Unexpected positional argument" in result["warnings"][0]


class TestEqualsFormLongFlags:
    """curl long options also accept `--flag=value` syntax."""

    def test_data_raw_equals_form(self):
        curl = (
            "curl --url https://example.com/api "
            "--header 'Content-Type: application/json' "
            "--data-raw='{\"a\":1}'"
        )
        result = CurlParser(curl).parse()
        assert result["method"] == "POST"
        assert result["url"] == "https://example.com/api"
        assert result["body_type"] == "json"
        assert result["body"] == {"a": 1}
        assert result["warnings"] == []

    def test_header_equals_form(self):
        result = CurlParser("curl --header='X-Custom: v' https://example.com").parse()
        assert result["headers"]["X-Custom"] == "v"
        assert result["warnings"] == []

    def test_method_equals_form(self):
        result = CurlParser("curl --request=PUT https://example.com").parse()
        assert result["method"] == "PUT"
        assert result["warnings"] == []


class TestHeadMethod:
    """-I / --head must map to a HEAD request and never eat the URL."""

    def test_short_head(self):
        result = CurlParser("curl -I https://example.com/api").parse()
        assert result["method"] == "HEAD"
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []

    def test_long_head(self):
        result = CurlParser("curl --head https://example.com/api").parse()
        assert result["method"] == "HEAD"
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []

    def test_head_combined_with_silent(self):
        # `curl -sI URL` — a very common ad-hoc probing command.
        result = CurlParser("curl -sI https://example.com/api").parse()
        assert result["method"] == "HEAD"
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []


class TestUserAgentAndReferer:
    def test_user_agent_flag(self):
        result = CurlParser(
            "curl -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' https://example.com"
        ).parse()
        assert result["headers"]["User-Agent"].startswith("Mozilla/5.0")
        assert result["warnings"] == []

    def test_referer_flag(self):
        result = CurlParser("curl -e 'https://example.com/page' https://example.com/api").parse()
        assert result["headers"]["Referer"] == "https://example.com/page"
        assert result["warnings"] == []


class TestJsonLongOption:
    def test_json_flag_sets_post_and_content_type(self):
        result = CurlParser("curl --json '{\"plateNo\":\"晋K88680\"}' https://example.com/api").parse()
        assert result["method"] == "POST"
        assert result["url"] == "https://example.com/api"
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["body_type"] == "json"
        assert result["body"] == {"plateNo": "晋K88680"}
        assert result["warnings"] == []


class TestOAuth2BearerFlag:
    def test_oauth2_bearer_creates_authorization_header(self):
        result = CurlParser(
            "curl --oauth2-bearer 'tok123' https://example.com/api"
        ).parse()
        assert result["headers"]["Authorization"] == "Bearer tok123"
        assert result["auth"]["type"] == "bearer"
        assert result["warnings"] == []


class TestUnknownFlagsKeepTheUrl:
    """Regression guard: an unrecognised flag must never swallow the URL that
    follows it (the original --url bug had the same shape)."""

    def test_unknown_boolean_flag_before_url(self):
        result = CurlParser("curl -z https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert any("Unrecognized flag" in w for w in result["warnings"])

    def test_unknown_value_flag_before_url(self):
        # The orphan value is reported as positional junk, but the URL survives.
        result = CurlParser("curl --definitely-not-a-flag '#@!' https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert any("Unrecognized flag" in w for w in result["warnings"])

    def test_unknown_flag_after_url(self):
        result = CurlParser("curl https://example.com/api --whatever").parse()
        assert result["url"] == "https://example.com/api"
        assert any("Unrecognized flag" in w for w in result["warnings"])


class TestCommonExportedFlagsAreNoop:
    """Flags from browser/API-client exports that don't affect request shape."""

    def test_timeout_retry_output_before_url(self):
        curl = (
            "curl --max-time 30 --connect-timeout 5 --retry 2 --retry-delay 1 "
            "-m 60 -o response.json -w '%{http_code}' "
            "-i --http2 --compressed https://example.com/api"
        )
        result = CurlParser(curl).parse()
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []

    def test_combined_short_flags_are_case_sensitive(self):
        # -sS === silent, -k === insecure; -I must stay HEAD not --include
        result = CurlParser("curl -skI https://example.com/api").parse()
        assert result["method"] == "HEAD"
        assert result["insecure"] is True
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []

    def test_output_dash_value_is_consumed(self):
        result = CurlParser("curl -sS -o - https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []

    def test_cookie_jar_is_ignored_silently(self):
        result = CurlParser("curl -c cookies.txt https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert result["warnings"] == []


class TestUnsupportedFlagsWarnButKeepUrl:
    def test_proxy_warns(self):
        result = CurlParser(
            "curl -x http://proxy.local:8080 https://example.com/api"
        ).parse()
        assert result["url"] == "https://example.com/api"
        assert any("--proxy" in w or "-x" in w for w in result["warnings"])

    def test_digest_auth_warns(self):
        result = CurlParser("curl --digest -u 'u:p' https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert any("--digest" in w for w in result["warnings"])

    def test_client_cert_warns(self):
        result = CurlParser("curl --cert client.pem --key key.pem https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert any("--cert" in w for w in result["warnings"])

    def test_get_flag_warns(self):
        result = CurlParser("curl -G -d 'a=1&b=2' https://example.com/api").parse()
        assert result["url"] == "https://example.com/api"
        assert any("--get" in w or "-G" in w for w in result["warnings"])
