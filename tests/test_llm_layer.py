"""LLM layer: JSON extraction, response shapes, and the provider registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_recap.core.config import Config, ConfigError
from manga_recap.llm.base import (
    LLMError,
    LLMResponseError,
    RetryPolicy,
    extract_json,
    is_quota_exhausted,
    normalise_panels,
)
from manga_recap.llm.registry import build_provider

# -- extract_json -----------------------------------------------------------


def test_plain_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_object_in_a_markdown_fence():
    text = 'Here you go:\n```json\n{"a": 1, "b": "x"}\n```\nHope that helps.'
    assert extract_json(text) == {"a": 1, "b": "x"}


def test_object_embedded_in_prose():
    text = 'Sure! {"a": 1} Hope that helps.'
    assert extract_json(text) == {"a": 1}


def test_nested_braces_are_matched_correctly():
    text = 'x {"outer": {"inner": 1}} y'
    assert extract_json(text) == {"outer": {"inner": 1}}


def test_braces_inside_strings_do_not_confuse_the_matcher():
    text = '{"text": "a } brace inside a string"}'
    assert extract_json(text) == {"text": "a } brace inside a string"}


def test_escaped_quotes_inside_strings():
    text = r'{"text": "she said \"hi\""}'
    assert extract_json(text) == {"text": 'she said "hi"'}


def test_a_top_level_list_is_wrapped():
    assert extract_json('[{"a": 1}]') == {"items": [{"a": 1}]}


def test_empty_response_is_an_error():
    with pytest.raises(LLMResponseError, match="Empty response"):
        extract_json("")


def test_non_json_response_is_an_error():
    with pytest.raises(LLMResponseError, match="Could not parse JSON"):
        extract_json("I am afraid I cannot do that.")


def test_malformed_json_is_an_error():
    with pytest.raises(LLMResponseError):
        extract_json('{"a": ')


def test_error_message_includes_a_preview():
    with pytest.raises(LLMResponseError) as exc:
        extract_json("totally not json at all, not even close")
    assert "totally not json" in str(exc.value)


# -- normalise_panels -------------------------------------------------------


def test_panels_key_is_used():
    assert normalise_panels({"panels": [{"a": 1}]}) == [{"a": 1}]


def test_items_key_is_used():
    assert normalise_panels({"items": [{"a": 1}]}) == [{"a": 1}]


def test_unlisted_key_with_dicts_is_found():
    assert normalise_panels({"unexpected": [{"a": 1}]}) == [{"a": 1}]


def test_non_dict_entries_are_dropped():
    assert normalise_panels({"panels": [{"a": 1}, "junk", 3]}) == [{"a": 1}]


def test_no_panel_list_is_an_error():
    with pytest.raises(LLMResponseError, match="Could not find a list of panels"):
        normalise_panels({"title": "no panels here"})


# -- retry policy -----------------------------------------------------------


def test_retry_succeeds_after_transient_failures():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("rate limit exceeded")
        return "ok"

    policy = RetryPolicy(max_retries=3, initial_backoff=0.001, max_backoff=0.002)
    assert policy.run(flaky) == "ok"
    assert attempts["n"] == 3


def test_retry_gives_up_and_reports():
    def always_fails():
        raise RuntimeError("503 service unavailable")

    policy = RetryPolicy(max_retries=2, initial_backoff=0.001, max_backoff=0.002)
    with pytest.raises(Exception, match="after 3 attempts"):
        policy.run(always_fails)


def test_fatal_errors_are_not_retried():
    attempts = {"n": 0}

    def unauthorised():
        attempts["n"] += 1
        raise RuntimeError("401 invalid api key")

    policy = RetryPolicy(max_retries=5, initial_backoff=0.001)
    with pytest.raises(Exception, match="not retryable"):
        policy.run(unauthorised)
    assert attempts["n"] == 1, "a bad key must fail immediately, not burn five retries"


def test_backoff_grows_and_is_capped():
    policy = RetryPolicy(initial_backoff=1.0, max_backoff=4.0, multiplier=2.0)
    delays = [policy.delay_for(i) for i in range(6)]
    # Jittered by half, so compare the upper bound of each.
    assert all(d <= 4.0 for d in delays)
    assert delays[0] < delays[-1]


# -- gemini wire format -----------------------------------------------------


def test_gemini_image_parts_use_the_camel_case_the_rest_api_expects(tmp_path):
    """The REST API rejects snake_case with a 400 naming the field.

    Nothing catches this until a real request goes out, and stage 2 is the first
    stage that talks to Gemini at all, so the wire format is pinned here instead
    of being discovered on a paid run. The Python SDK accepts either spelling,
    which is exactly why the mistake survives locally.

    The whole part is asserted, not just the inner object, because wrapping the
    part in a second `inlineData` produces the same class of error and is just
    as invisible locally.
    """
    from PIL import Image

    from manga_recap.llm.gemini import _inline_data

    image = tmp_path / "panel_0001.png"
    Image.new("RGB", (4, 4), (255, 255, 255)).save(image)

    part = _inline_data(image)

    assert set(part) == {"inlineData"}
    assert set(part["inlineData"]) == {"mimeType", "data"}
    assert part["inlineData"]["mimeType"] == "image/png"
    assert part["inlineData"]["data"]
    assert "inline_data" not in str(part)
    assert "mime_type" not in str(part)


@pytest.mark.parametrize(
    "suffix,mime",
    [("png", "image/png"), ("jpg", "image/jpeg"), ("webp", "image/webp")],
)
def test_gemini_mime_types_cover_what_the_pipeline_writes(suffix, mime):
    from manga_recap.llm.gemini import _mime_for

    assert _mime_for(Path(f"panel_0001.{suffix}")) == mime


# -- registry ---------------------------------------------------------------


def base_config(provider="anthropic", model="test-model"):
    return Config(
        {
            "llm": {
                "vision": {"provider": provider, "model": model},
                "script": {"provider": provider, "model": model},
            },
            "crop": {"detector": "opencv"},
        }
    )


def test_registry_builds_an_anthropic_provider(set_env):
    set_env({"ANTHROPIC_API_KEY": "k"})
    provider = build_provider(base_config("anthropic"), "vision")
    assert provider.name == "anthropic"
    assert provider.model == "test-model"


def test_registry_builds_a_gemini_provider(set_env):
    set_env({"GEMINI_API_KEY": "k"})
    provider = build_provider(base_config("gemini"), "vision")
    assert provider.name == "gemini"


def test_registry_builds_an_openrouter_provider(set_env):
    set_env({"OPENROUTER_API_KEY": "k"})
    provider = build_provider(base_config("openrouter"), "vision")
    assert provider.name == "openrouter"


def test_vision_and_script_can_use_different_providers(set_env):
    set_env({"ANTHROPIC_API_KEY": "k", "GEMINI_API_KEY": "g"})
    config = Config(
        {
            "llm": {
                "vision": {"provider": "gemini", "model": "gemini-model"},
                "script": {"provider": "anthropic", "model": "claude-model"},
            },
            "crop": {"detector": "opencv"},
        }
    )
    assert build_provider(config, "vision").name == "gemini"
    assert build_provider(config, "script").name == "anthropic"


def test_missing_api_key_names_the_variable(set_env):
    set_env({})
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        build_provider(base_config("gemini"), "vision")


def test_unknown_role_is_rejected():
    with pytest.raises(ConfigError, match="Unknown LLM role"):
        build_provider(base_config(), "translator")


def test_per_role_retries_override_the_shared_default(set_env):
    """The two roles face different load, and only the vision role sees 503s.

    A supplied policy used to win over the provider's own `max_retries`
    argument, which made the documented per-role key dead config: setting it to
    6 still produced three attempts.
    """
    set_env({"GEMINI_API_KEY": "k"})
    config = Config(
        {
            "llm": {
                "vision": {
                    "provider": "gemini",
                    "model": "m",
                    "max_retries": 6,
                },
                "script": {"provider": "gemini", "model": "m"},
                "retry": {"max_retries": 2},
            }
        }
    )

    assert build_provider(config, "vision").retry.max_retries == 6
    assert build_provider(config, "script").retry.max_retries == 2


def test_shared_retry_count_is_used_when_a_role_is_silent(set_env):
    set_env({"GEMINI_API_KEY": "k"})
    config = Config(
        {
            "llm": {
                "vision": {"provider": "gemini", "model": "m"},
                "script": {"provider": "gemini", "model": "m"},
                "retry": {"max_retries": 5, "initial_backoff_seconds": 5.0},
            }
        }
    )

    policy = build_provider(config, "vision").retry

    assert policy.max_retries == 5
    assert policy.initial_backoff == 5.0


# -- quota versus rate limit ------------------------------------------------


def test_exhausted_quota_is_distinguished_from_a_rate_limit():
    """Both arrive as 429 and need opposite responses.

    A rate limit clears in seconds, so a retry is right. An exhausted allowance
    does not clear inside this process's lifetime, and six retries turn a
    five-second answer into a four-minute one that changes nothing.
    """
    exhausted = (
        "429 RESOURCE_EXHAUSTED: Quota exceeded for metric: "
        "generate_content_free_tier_requests, limit: 20, model: gemini-3.8-flash"
    )
    throttled = "429 Too Many Requests. Please retry in 7.4s."

    assert is_quota_exhausted(exhausted) is True
    assert is_quota_exhausted(throttled) is False


def test_quota_errors_are_not_retried():
    """Retrying an exhausted quota is the bug this classification exists to stop."""
    from manga_recap.llm.base import LLMQuotaError

    calls = {"n": 0}

    def always_over_quota():
        calls["n"] += 1
        raise LLMQuotaError("quota exhausted, limit: 20")

    policy = RetryPolicy(max_retries=6, initial_backoff=0.0)

    with pytest.raises(LLMQuotaError):
        policy.run(always_over_quota, description="vision")
    assert calls["n"] == 1


def test_a_rate_limit_is_still_retried():
    calls = {"n": 0}

    def throttled():
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMError("429 Too Many Requests")

        return "ok"

    policy = RetryPolicy(max_retries=6, initial_backoff=0.0)

    assert policy.run(throttled, description="vision") == "ok"
    assert calls["n"] == 3


def test_the_quota_hint_names_the_limit_and_the_metric():
    """The two facts that decide whether to enable billing or just wait."""
    from manga_recap.llm.gemini import _quota_hint

    hint = _quota_hint(
        "Quota exceeded for metric: generativelanguage.googleapis.com/"
        "generate_content_free_tier_requests, limit: 20, model: gemini-3.8-flash"
    )

    assert "limit 20" in hint
    assert "free_tier_requests" in hint


# A real free-tier overrun, verbatim in the parts that matter. The body is the
# only place the window is stated, and getting it wrong is what turns a
# ten-hour wait into a ten-minute one.
DAILY_QUOTA_BODY = """{
  "error": {
    "code": 429,
    "message": "You exceeded your current quota\\n* Quota exceeded for metric:
      generativelanguage.googleapis.com/generate_content_free_tier_requests,
      limit: 20, model: gemini-3.5-flash\\nPlease retry in 10h33m25s.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
       "violations": [{"quotaId":
         "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]},
      {"@type": "type.googleapis.com/google.rpc.RetryInfo",
       "retryDelay": "38005s"}
    ]
  }
}"""


def test_the_quota_hint_names_the_window_because_the_metric_does_not():
    """`free_tier_requests` says nothing about the window; the quotaId does.

    Reading the limit as "20 requests a minute" is the mistake this prevents.
    The free tier is 20 a *day*, and the id is the only field that says so.
    """
    from manga_recap.llm.gemini import _quota_hint

    hint = _quota_hint(DAILY_QUOTA_BODY)

    assert "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in hint


def test_the_retry_delay_is_read_out_of_the_quota_body():
    """A daily window is quoted in hours, and that number is what to sleep for."""
    from manga_recap.llm.gemini import _retry_after_seconds

    assert _retry_after_seconds(DAILY_QUOTA_BODY) == 38005.0


def test_the_retry_delay_survives_the_error_body_the_provider_keeps():
    """The body is truncated for the message, and the delay sits at the end.

    A real overrun buries `RetryInfo` after the help links and the quota
    failure, well past a short prefix. Truncating to 600 characters kept a
    clean error message and silently deleted the only number in the response
    that says when to come back.
    """
    from manga_recap.llm.base import LLMQuotaError
    from manga_recap.llm.gemini import GeminiProvider

    body = DAILY_QUOTA_BODY.replace("\\n", "\n")
    # Pad the front the way a real body is padded by its help links and
    # metrics, so RetryInfo really does fall outside a short prefix.
    padded = "{" + " " * 700 + body[1:]

    class _Response:
        status_code = 429
        text = padded

    class _Client:
        def post(self, *args, **kwargs):
            return _Response()

    provider = GeminiProvider(api_key="k", model="gemini-3.5-flash")
    provider._client = _Client()

    with pytest.raises(LLMQuotaError) as caught:
        provider._generate(
            system="s", parts=[], response_schema={}, max_tokens=1, temperature=0.0
        )

    assert caught.value.retry_after == 38005.0
    # And the slice the provider reads has to be long enough to contain it.
    assert '"retryDelay"' in padded[:2000]


def test_a_quota_error_carries_its_retry_delay_to_the_caller():
    """The delay has to survive the raise, or nobody downstream can use it.

    Wrapping or re-raising an error from its message is what silently drops
    every attribute on it, and a job that waits out a closed window depends on
    this one number.
    """
    from manga_recap.llm.base import LLMQuotaError

    original = LLMQuotaError("quota exhausted, limit: 20", retry_after=38005.0)

    assert original.retry_after == 38005.0
    assert LLMQuotaError("no delay given").retry_after is None
