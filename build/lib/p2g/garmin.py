import httpx
import re
import urllib.parse
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from oauthlib.oauth1 import Client as OAuth1Client
from .config import Settings

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

    def __init__(self, settings: Settings):
        self.settings = settings.Garmin
        self.client = httpx.Client(follow_redirects=True)
        self.oauth2_token = None
        self.consumer_key = "fc3e99d2-118c-44b8-8ae3-03370dde24c0"
        self.consumer_secret = "E08WAR897WEy2knn7aFBrvegVAf0AFdWBBF"

    def authenticate(self):
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
        resp = self.client.post(
            self.settings.Api.SsoSignInUrl,
            params=self.COMMON_QUERY_PARAMS,
            data=login_data,
            follow_redirects=False
        )

        # 4. Handle MFA if needed
        if resp.status_code == 302 and "verifyMFA" in resp.headers.get("Location", ""):
            # Re-fetch the MFA page to get new CSRF
            mfa_url = resp.headers["Location"]
            resp = self.client.get(mfa_url)
            mfa_csrf = self._extract_csrf(resp.text)
            
            print("Detected Garmin MFA. Please enter the code sent to your device:")
            mfa_code = input("MFA Code: ")
            
            mfa_data = {
                "embed": "true",
                "mfa-code": mfa_code,
                "fromPage": "setupEnterMfaCode",
                "_csrf": mfa_csrf
            }
            resp = self.client.post(
                "https://sso.garmin.com/sso/verifyMFA/loginEnterMfaCode",
                params=self.COMMON_QUERY_PARAMS,
                data=mfa_data,
                follow_redirects=True
            )

        # 5. Extract Service Ticket
        # The result of a successful login is often 200 with the ticket in JS or similar.
        # Searching for ticket=...
        ticket_match = re.search(r'embed\?ticket=([^"]+)"', resp.text)
        if not ticket_match:
            raise Exception("Failed to find service ticket in Garmin response.")
        ticket = ticket_match.group(1)

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
            "User-Agent": "GCM-iOS-5.7.2.1"
        }
        
        files = {"file": (open(file_path, "rb"), "application/octet-stream")}
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
