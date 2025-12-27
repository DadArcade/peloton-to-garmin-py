import httpx
import re
import urllib.parse
import time
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from oauthlib.oauth1 import Client as OAuth1Client
from .config import Settings, save_garmin_tokens

class GarminClient:
    COMMON_QUERY_PARAMS = {
        "id": "gauth-widget",
        "embedWidget": "true",
        "gauthHost": "https://sso.garmin.com/sso/embed",
        "redirectAfterAccountCreationUrl": "https://sso.garmin.com/sso/embed",
        "redirectAfterAccountLoginUrl": "https://sso.garmin.com/sso/embed",
        "service": "https://sso.garmin.com/sso/embed",
        "source": "https://sso.garmin.com/sso/embed",
    }

    def __init__(self, settings: Settings, config_path: str = "config.toml"):
        self.settings = settings.Garmin
        self.config_path = config_path
    def __init__(self, settings: Settings, config_path: str = "config.toml"):
        self.settings = settings.Garmin
        self.config_path = config_path
        self.client = httpx.Client(follow_redirects=True)
        self.client.headers.update({
            "User-Agent": "GCM-iOS-5.7.2.1",
            "origin": "https://sso.garmin.com"
        })
        self.oauth2_token = None
        self.consumer_key = "fc3e99d2-118c-44b8-8ae3-03370dde24c0"
        self.consumer_secret = "E08WAR897WEy2knn7aFBrvegVAf0AFdWBBF"

    def authenticate(self):
        # 0. Try using saved OAuth1 tokens if available
        if self.settings.OAuth1Token and self.settings.OAuth1TokenSecret:
            try:
                print("Found saved Garmin tokens, attempting to skip login...")
                self._exchange_oauth1_for_oauth2(
                    self.settings.OAuth1Token, 
                    self.settings.OAuth1TokenSecret
                )
                print("Authenticated using saved tokens.")
                return
            except Exception as e:
                print(f"Saved tokens failed (expired?), falling back to full login. Error: {e}")

        max_retries = 10
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                self._authenticate()
                return
            except Exception as e:
                is_429 = "429" in str(e)
                
                if is_429 and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Garmin authentication failed with 429. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    # Reset client to clear potential session issues
                    self.client = httpx.Client(follow_redirects=True)
                else:
                    raise e


    def _authenticate(self):
        # 1. Init Auth Flow
        self.client.get(
            self.settings.Api.SsoSignInUrl,
            params=self.COMMON_QUERY_PARAMS,
            headers={"User-Agent": "GCM-iOS-5.7.2.1"}
        )

        # 2. Get CSRF Token
        resp = self.client.get(
            self.settings.Api.SsoSignInUrl,
            params=self.COMMON_QUERY_PARAMS
        )
        csrf_token = self._extract_csrf(resp.text)

        # 3. Send Credentials
        login_data = {
            "username": self.settings.Email,
            "password": self.settings.Password,
            "embed": "true",
            "_csrf": csrf_token
        }
        
        # Match C# headers exactly (GCM-iOS-5.7.2.1)
        # Note: We set global headers in __init__ but we add specific ones here
        login_headers = {
            "referer": f"https://sso.garmin.com/sso/signin?{urllib.parse.urlencode(self.COMMON_QUERY_PARAMS)}",
            "NK": "NT"
        }

        resp = self.client.post(
            self.settings.Api.SsoSignInUrl,
            params=self.COMMON_QUERY_PARAMS,
            data=login_data,
            headers=login_headers,
            follow_redirects=True
        )

        # 4. Handle MFA if needed (even after redirects, we might land on the MFA page)
        if "verifyMFA" in str(resp.url):
            mfa_csrf = self._extract_csrf(resp.text)
            
            print("Detected Garmin MFA. Please enter the code sent to your device:")
            mfa_code = input("MFA Code: ")
            
            mfa_data = {
                "embed": "true",
                "mfa-code": mfa_code,
                "fromPage": "setupEnterMfaCode",
                "_csrf": mfa_csrf
            }
            
            # Use headers for MFA too
            mfa_headers = {
                 "referer": str(resp.url).split('?')[0], # The MFA page we just came from
                 "NK": "NT"
            }
            
            resp = self.client.post(
                "https://sso.garmin.com/sso/verifyMFA/loginEnterMfaCode",
                params=self.COMMON_QUERY_PARAMS,
                data=mfa_data,
                headers=mfa_headers,
                follow_redirects=True
            )

        if "invalid" in resp.text.lower() or "incorrect" in resp.text.lower():
             raise Exception("Garmin Login Failed: Check your email and password.")

        if resp.status_code != 200:
            snippet = resp.text[:500].replace('\n', ' ')
            raise Exception(f"Garmin login failed with status {resp.status_code}. body: {snippet}")

        # 5. Extract Service Ticket
        # Using the exact regex pattern from C#
        ticket_match = re.search(r'embed\?ticket=(?P<ticket>[^"]+)"', resp.text)
        if not ticket_match:
            snippet = resp.text[:1000].replace('\n', ' ')
            raise Exception(f"Failed to find service ticket in Garmin response. status={resp.status_code}, url={resp.url}, body_snippet={snippet}")
        ticket = ticket_match.group("ticket")

        # 6. Exchange Ticket for OAuth1 Token
        oauth1_url = f"https://connectapi.garmin.com/oauth-service/oauth/preauthorized?ticket={ticket}&login-url=https://sso.garmin.com/sso/embed&accepts-mfa-tokens=true"
        oauth1_client = OAuth1Client(self.consumer_key, client_secret=self.consumer_secret)
        uri, headers, body = oauth1_client.sign(oauth1_url)
        resp = self.client.get(uri, headers=headers)
        resp.raise_for_status()
        
        token_qs = urllib.parse.parse_qs(resp.text)
        oauth1_token = token_qs["oauth_token"][0]
        oauth1_token_secret = token_qs["oauth_token_secret"][0]

        # 7. Exchange OAuth1 for OAuth2
        self._exchange_oauth1_for_oauth2(oauth1_token, oauth1_token_secret)
        
        # 8. Save tokens
        print("Saving Garmin tokens for future use...")
        save_garmin_tokens(self.config_path, oauth1_token, oauth1_token_secret)

    def _exchange_oauth1_for_oauth2(self, oauth1_token, oauth1_token_secret):
        oauth2_url = "https://connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0"
        oauth1_client = OAuth1Client(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=oauth1_token,
            resource_owner_secret=oauth1_token_secret
        )
        uri, headers, body = oauth1_client.sign(oauth2_url, http_method="POST")
        # Add required content-type that Flurl hack did
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        resp = self.client.post(uri, headers=headers, data={})
        resp.raise_for_status()
        
        self.oauth2_token = resp.json()

    def upload_activity(self, file_path: str, file_format: str = "fit"):
        if not self.oauth2_token:
            raise Exception("Not authenticated with Garmin.")

        url = f"{self.settings.Api.UploadActivityUrl}/{file_format}"
        headers = {
            "Authorization": f"Bearer {self.oauth2_token['access_token']}",
            "NK": "NT",
            "origin": "https://sso.garmin.com",
            "User-Agent": "GCM-iOS-5.7.2.1",
            "Accept": "application/json"
        }
        
        import os
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            # Garmin can be picky about the multipart structure
            files = {"file": (filename, f, "application/octet-stream")}
            resp = self.client.post(url, headers=headers, files=files)
        
        if resp.status_code == 409:
            print(f"Activity {file_path} already uploaded.")
        else:
            resp.raise_for_status()
            print(f"Successfully uploaded {file_path} to Garmin.")

    def _extract_csrf(self, html: str) -> str:
        match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
        if not match:
            # Try BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            csrf_input = soup.find('input', attrs={'name': '_csrf'})
            if csrf_input:
                return csrf_input.get('value')
            raise Exception("CSRF token not found in Garmin response.")
        return match.group(1)
