import os
import pytest
import time
from unittest.mock import MagicMock, patch
from p2g.garmin import GarminClient

def test_garmin_retry():
    settings = MagicMock()
    settings.Garmin.Email = "test@example.com"
    settings.Garmin.Password = "password"
    settings.Garmin.Api.SsoSignInUrl = "https://sso.garmin.com"
    
    client = GarminClient(settings)
    
    # Mock _authenticate to fail twice with 429 and then succeed
    call_count = 0
    def mock_auth_inner():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception("Garmin login failed with status 429. body: Cloudflare blocks you")
        return

    client._authenticate = mock_auth_inner
    
    # Mock sleep to speed up test
    with patch("time.sleep", return_value=None):
        start_time = time.time()
        client.authenticate()
        duration = time.time() - start_time
    
    assert call_count == 3
    assert duration < 1.0 # Should be instant due to mock sleep
