import httpx
import base64
import hashlib
import secrets
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .config import Settings

class PelotonClient:
    def __init__(self, settings: Settings):
        self.settings = settings.Peloton
        self.client = httpx.Client(follow_redirects=True)
        self.access_token = None
        self.user_id = None

    def authenticate(self):
        # PKCE Setup
        verifier = self._generate_random_string(64)
        challenge = self._generate_code_challenge(verifier)
        state = self._generate_random_string(32)
        nonce = self._generate_random_string(32)

        # Use a consistent user agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.client.headers.update({
            "User-Agent": user_agent,
            "Peloton-Platform": "web"
        })

        # 1. Initiate Auth Flow
        params = {
            "client_id": self.settings.Api.AuthClientId,
            "audience": "https://api.onepeloton.com/",
            "scope": "offline_access openid peloton-api.members:default",
            "response_type": "code",
            "response_mode": "query",
            "redirect_uri": "https://members.onepeloton.com/callback",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"https://{self.settings.Api.AuthDomain}/authorize?{urllib.parse.urlencode(params)}"

        resp = self.client.get(auth_url)
        
        # Capture updated state if redirected
        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(str(resp.url)).query)
        if "state" in query_params:
            state = query_params["state"][0]

        # Extract CSRF token from cookies
        csrf_token = None
        for cookie in self.client.cookies.jar:
            if cookie.name == "_csrf" and "onepeloton.com" in cookie.domain:
                csrf_token = cookie.value
                break
        
        if not csrf_token:
            raise Exception("Failed to find CSRF token for Peloton login. check if cookies are being blocked or site structure changed.")

        # 2. Submit Credentials
        login_payload = {
            "client_id": self.settings.Api.AuthClientId,
            "redirect_uri": "https://members.onepeloton.com/callback",
            "tenant": "peloton-prod",
            "response_type": "code",
            "scope": "offline_access openid peloton-api.members:default",
            "audience": "https://api.onepeloton.com/",
            "username": self.settings.Email,
            "password": self.settings.Password,
            "connection": "pelo-user-password",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "_csrf": csrf_token,
            "_intstate": "deprecated"
        }

        login_url = f"https://{self.settings.Api.AuthDomain}/usernamepassword/login"
        login_headers = {
            "Origin": f"https://{self.settings.Api.AuthDomain}",
            "Referer": str(resp.url),
            "Auth0-Client": "eyJuYW1lIjoiYXV0aDAuanMtdWxwIiwidmVyc2lvbiI6IjkuMTQuMyJ9" # Same as C# version
        }
        
        resp = self.client.post(
            login_url, 
            json=login_payload, 
            headers=login_headers,
            follow_redirects=False
        )

        # 3. Follow Redirects to get Code
        # It might be a 302, 200 with a form, or 200 with an error
        next_url = None
        if resp.status_code == 302:
            next_url = resp.headers.get("Location")
        elif resp.status_code == 200:
            if "wrong email or password" in resp.text.lower():
                 raise Exception("Peloton Login Failed: Wrong email or password.")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            form = soup.find('form')
            if form:
                action = form.get('action')
                if not action.startswith("http"):
                    action = f"https://{self.settings.Api.AuthDomain}{action}"
                hidden_fields = {i.get('name'): i.get('value') for i in form.find_all('input', type='hidden')}
                resp = self.client.post(action, data=hidden_fields, follow_redirects=True)
                next_url = str(resp.url)
        
        if next_url:
            if not next_url.startswith("http"):
                next_url = f"https://{self.settings.Api.AuthDomain}{next_url}"
            resp = self.client.get(next_url, follow_redirects=True)

        final_url = str(resp.url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(final_url).query)
        code = query.get("code", [None])[0]

        if not code:
            # Better diagnostics on failure
            snippet = resp.text[:1000].replace('\n', ' ')
            raise Exception(f"Failed to get authorization code from Peloton. status={resp.status_code}, url={final_url}, body_snippet={snippet}")

        # 4. Exchange Code for Token
        token_url = f"https://{self.settings.Api.AuthDomain}/oauth/token"
        token_payload = {
            "grant_type": "authorization_code",
            "client_id": self.settings.Api.AuthClientId,
            "code_verifier": verifier,
            "code": code,
            "redirect_uri": "https://members.onepeloton.com/callback"
        }
        resp = self.client.post(token_url, json=token_payload)
        resp.raise_for_status()
        token_data = resp.json()
        self.access_token = token_data["access_token"]

        # 5. Get User ID
        me_resp = self.client.get(
            f"{self.settings.Api.ApiUrl}api/me",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        me_resp.raise_for_status()
        self.user_id = me_resp.json()["id"]

    def get_recent_workouts(self, limit: int = 5) -> List[Dict[str, Any]]:
        url = f"{self.settings.Api.ApiUrl}api/user/{self.user_id}/workouts"
        params = {
            "limit": limit,
            "sort_by": "-created",
            "joins": "ride,ride.instructor"
        }
        resp = self.client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def get_workout_details(self, workout_id: str) -> Dict[str, Any]:
        url = f"{self.settings.Api.ApiUrl}api/workout/{workout_id}"
        params = {"joins": "ride,ride.instructor"}
        resp = self.client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        resp.raise_for_status()
        return resp.json()

    def get_performance_graph(self, workout_id: str) -> Dict[str, Any]:
        url = f"{self.settings.Api.ApiUrl}api/workout/{workout_id}/performance_graph"
        params = {"every_n": 1}
        resp = self.client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        resp.raise_for_status()
        return resp.json()

    def get_class_segments(self, class_id: str) -> Dict[str, Any]:
        url = f"{self.settings.Api.ApiUrl}api/ride/{class_id}/details"
        try:
            resp = self.client.get(
                url, headers={"Authorization": f"Bearer {self.access_token}"}
            )
            resp.raise_for_status()  # will raise for 404, 500, etc.
            return resp.json()
        except httpx.HTTPStatusError as exc:
            # 404 means the class has no segment data (e.g., scenic or non‑subscribed)
            if exc.response.status_code == 404:
                return {}
            # Any other status code is unexpected – re‑raise so we notice it
            raise

    def get_me(self) -> Dict[str, Any]:
        url = f"{self.settings.Api.ApiUrl}api/me"
        resp = self.client.get(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        resp.raise_for_status()
        return resp.json()

    def _generate_random_string(self, length: int) -> str:
        res = secrets.token_urlsafe(length)
        return res[:length].replace('+', '-').replace('/', '_').replace('=', '')

    def _generate_code_challenge(self, verifier: str) -> str:
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
