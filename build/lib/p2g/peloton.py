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

        # 1. Initiate Auth Flow
        auth_url = (
            f"https://{self.settings.Api.AuthDomain}/authorize?"
            + urllib.parse.urlencode({
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
            })
        )

        resp = self.client.get(auth_url)
        # Auth0 usually drops a CSRF cookie here.
        csrf_token = self.client.cookies.get("_csrf")
        if not csrf_token:
            # Sometimes it's in the page? But usually cookie. 
            # If not found, we might need to follow more redirects.
            pass

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
            "_csrf": csrf_token
        }

        login_url = f"https://{self.settings.Api.AuthDomain}/usernamepassword/login"
        resp = self.client.post(login_url, json=login_payload, follow_redirects=False)

        # 3. Follow Redirects to get Code
        # This part can be tricky as it might return a form that auto-submits.
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            form = soup.find('form')
            if form:
                action = form.get('action')
                hidden_fields = {i.get('name'): i.get('value') for i in form.find_all('input', type='hidden')}
                resp = self.client.post(action, data=hidden_fields)

        # The final redirect should have the code in the query params.
        # httpx followed it if we set follow_redirects=True in the post or subsequent get.
        final_url = str(resp.url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(final_url).query)
        code = query.get("code", [None])[0]

        if not code:
            raise Exception(f"Failed to get authorization code from Peloton. Final URL: {final_url}")

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

    def _generate_random_string(self, length: int) -> str:
        res = secrets.token_urlsafe(length)
        return res[:length].replace('+', '-').replace('/', '_').replace('=', '')

    def _generate_code_challenge(self, verifier: str) -> str:
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
