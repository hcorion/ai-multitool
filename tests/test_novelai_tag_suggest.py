"""
Tests for NovelAI tag suggestion functionality.

Covers NovelAIClient.suggest_tags() and the /novelai/suggest-tags Flask endpoint.
"""

import pytest
from unittest.mock import Mock, patch

from novelai_client import NovelAIClient, NovelAIAPIError, NovelAIClientError


# ---------------------------------------------------------------------------
# NovelAIClient.suggest_tags unit tests
# ---------------------------------------------------------------------------

class TestSuggestTags:
    def _make_client(self):
        return NovelAIClient("test-key")

    def _mock_get(self, client, json_body, status_code=200):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_body
        client.session.get = Mock(return_value=mock_response)
        return mock_response

    def test_returns_tag_list(self):
        client = self._make_client()
        self._mock_get(client, {
            "tags": [
                {"tag": "1girl", "count": 500000, "confidence": 0.99},
                {"tag": "1girl, solo", "count": 200000, "confidence": 0.85},
            ]
        })

        result = client.suggest_tags("nai-diffusion-4-5-full", "1gir")

        assert len(result) == 2
        assert result[0]["tag"] == "1girl"
        assert result[0]["count"] == 500000

    def test_calls_correct_url_and_params(self):
        client = self._make_client()
        self._mock_get(client, {"tags": []})

        client.suggest_tags("nai-diffusion-4-5-full", "blue")

        client.session.get.assert_called_once_with(
            "https://image.novelai.net/ai/generate-image/suggest-tags",
            params={"model": "nai-diffusion-4-5-full", "prompt": "blue", "lang": "en"},
        )

    def test_empty_tags_list(self):
        client = self._make_client()
        self._mock_get(client, {"tags": []})

        result = client.suggest_tags("nai-diffusion-4-5-full", "zzz_no_match")

        assert result == []

    def test_missing_tags_key_returns_empty(self):
        """API response without 'tags' key should return empty list."""
        client = self._make_client()
        self._mock_get(client, {})

        result = client.suggest_tags("nai-diffusion-4-5-full", "blue")

        assert result == []

    def test_api_error_401(self):
        client = self._make_client()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        client.session.get = Mock(return_value=mock_response)

        with pytest.raises(NovelAIAPIError) as exc_info:
            client.suggest_tags("nai-diffusion-4-5-full", "blue")

        assert exc_info.value.status_code == 401
        assert "Unauthorized" in str(exc_info.value)

    def test_api_error_500(self):
        client = self._make_client()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}
        client.session.get = Mock(return_value=mock_response)

        with pytest.raises(NovelAIAPIError) as exc_info:
            client.suggest_tags("nai-diffusion-4-5-full", "blue")

        assert exc_info.value.status_code == 500

    def test_api_error_non_json_body(self):
        """Non-JSON error body should still raise NovelAIAPIError."""
        client = self._make_client()
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.side_effect = ValueError("not json")
        client.session.get = Mock(return_value=mock_response)

        with pytest.raises(NovelAIAPIError) as exc_info:
            client.suggest_tags("nai-diffusion-4-5-full", "blue")

        assert exc_info.value.status_code == 503

    def test_network_error_raises_client_error(self):
        import requests
        client = self._make_client()
        client.session.get = Mock(side_effect=requests.RequestException("timeout"))

        with pytest.raises(NovelAIClientError) as exc_info:
            client.suggest_tags("nai-diffusion-4-5-full", "blue")

        assert "Network error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Flask endpoint /novelai/suggest-tags
# ---------------------------------------------------------------------------

class TestSuggestTagsEndpoint:
    def _login(self, client):
        with client.session_transaction() as sess:
            sess["username"] = "testuser"

    def test_requires_auth(self, client):
        resp = client.get("/novelai/suggest-tags?prompt=blue&model=nai-diffusion-4-5-full")
        assert resp.status_code == 401

    def test_empty_prompt_returns_empty_tags(self, client):
        self._login(client)
        with patch("app.NOVELAI_API_KEY", "fake-key"):
            resp = client.get("/novelai/suggest-tags?prompt=&model=nai-diffusion-4-5-full")
        assert resp.status_code == 200
        assert resp.get_json() == {"tags": []}

    def test_missing_prompt_returns_empty_tags(self, client):
        self._login(client)
        with patch("app.NOVELAI_API_KEY", "fake-key"):
            resp = client.get("/novelai/suggest-tags?model=nai-diffusion-4-5-full")
        assert resp.status_code == 200
        assert resp.get_json() == {"tags": []}

    def test_no_api_key_returns_error(self, client):
        self._login(client)
        with patch("app.NOVELAI_API_KEY", None):
            resp = client.get("/novelai/suggest-tags?prompt=blue&model=nai-diffusion-4-5-full")
        assert resp.status_code == 400

    def test_returns_suggestions(self, client):
        self._login(client)
        tags = [{"tag": "blue eyes", "count": 100000, "confidence": 0.95}]

        with patch("app.NOVELAI_API_KEY", "fake-key"):
            with patch("app.NovelAIClient") as MockClient:
                MockClient.return_value.suggest_tags.return_value = tags
                resp = client.get("/novelai/suggest-tags?prompt=blue&model=nai-diffusion-4-5-full")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tags"] == tags

    def test_uses_default_model_when_omitted(self, client):
        self._login(client)

        with patch("app.NOVELAI_API_KEY", "fake-key"):
            with patch("app.NovelAIClient") as MockClient:
                MockClient.return_value.suggest_tags.return_value = []
                client.get("/novelai/suggest-tags?prompt=blue")
                MockClient.return_value.suggest_tags.assert_called_once()
                _, kwargs = MockClient.return_value.suggest_tags.call_args
                # model kwarg should be the default
                assert "model" in kwargs

    def test_novelai_api_error_returns_500(self, client):
        self._login(client)

        with patch("app.NOVELAI_API_KEY", "fake-key"):
            with patch("app.NovelAIClient") as MockClient:
                MockClient.return_value.suggest_tags.side_effect = NovelAIAPIError(401, "Unauthorized")
                resp = client.get("/novelai/suggest-tags?prompt=blue&model=nai-diffusion-4-5-full")

        assert resp.status_code == 500

    def test_novelai_client_error_returns_500(self, client):
        self._login(client)

        with patch("app.NOVELAI_API_KEY", "fake-key"):
            with patch("app.NovelAIClient") as MockClient:
                MockClient.return_value.suggest_tags.side_effect = NovelAIClientError("timeout")
                resp = client.get("/novelai/suggest-tags?prompt=blue&model=nai-diffusion-4-5-full")

        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Integration test (skipped without real key)
# ---------------------------------------------------------------------------

class TestSuggestTagsIntegration:
    @pytest.mark.integration
    def test_real_suggestions(self, skip_if_no_api_key):
        skip_if_no_api_key("novelai")
        import os
        client = NovelAIClient(os.environ["NOVELAI_API_KEY"])
        try:
            results = client.suggest_tags("nai-diffusion-4-5-full", "1gir")
            assert isinstance(results, list)
            assert len(results) > 0
            assert all("tag" in t for t in results)
        except NovelAIAPIError as e:
            # NovelAI's tag suggestion endpoint is known to return 500 server errors
            # for some models intermittently — skip rather than fail in that case
            if e.status_code == 500:
                pytest.skip(f"NovelAI tag suggestion API returned 500 (server-side issue): {e}")
            raise
