from datetime import datetime
import jwt
import requests
import logging
import json

_LOGGER = logging.getLogger(__name__)

class ThingsBoard:
    """eSTUDNA2 wrapper/ ThingsBoard API (API v2)."""

    def __init__(self):
        self.server = "https://cml5.seapraha.cz"
        self.userToken = None
        self.refreshToken = None
        self.user_id = None
        self.session = requests.Session()

    def http_request(self, method, url, headers=None, params=None, data=None, check_token=True):
        if check_token and self.token_expired:
            self.refresh_token()

        if headers is None:
            headers = {}
        headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        if self.userToken:
            headers["X-Authorization"] = f"Bearer {self.userToken}"

        try:
            response = self.session.request(
                method, f"{self.server}{url}", headers=headers, params=params, json=data, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error("HTTP request failed: %s", e)
            raise

    def http_post(self, url, data=None, check_token=True):
        return self.http_request("post", url, data=data, check_token=check_token)

    def http_get(self, url, params=None, check_token=True):
        return self.http_request("get", url, params=params, check_token=check_token)

    def login(self, username, password):
        """Login via API v2, getting token and user_id."""
        url = "/apiv2/auth/login"
        response = self.http_post(url, data={"username": username, "password": password}, check_token=False)

        self.userToken = response.get("token")
        self.refreshToken = response.get("refreshToken")
        self.user_id = response.get("user_id")

        if not self.userToken or not self.refreshToken or not self.user_id:
            raise Exception("Login failed: missing token or user_id")

        _LOGGER.info("Login successful, user_id: %s", self.user_id)

    def refresh_token(self):
        """Renewal of JWT token via API v2."""
        if not self.refreshToken:
            raise Exception("No refresh token available. Please login first.")

        response = self.http_post("/apiv2/auth/token", data={"refreshToken": self.refreshToken}, check_token=False)
        self.userToken = response["token"]
        self.refreshToken = response["refreshToken"]
        _LOGGER.info("Token successfully renewed")

    @property
    def token_expired(self):
        if not self.userToken:
            return True
        decoded = jwt.decode(self.userToken, options={"verify_signature": False})
        expiry_time = datetime.fromtimestamp(decoded["exp"])
        return expiry_time <= datetime.now()

    def get_devices(self):
        """Getting the list of devices for actual user"""
        if not self.user_id:
            raise Exception("No user_id. Please login first.")

        # Corretn endpoint for devices 
        resp = self.http_get(f"/apiv2/user/{self.user_id}/devices")
        # API returns the list 
        devices = resp if isinstance(resp, list) else resp.get("data", [])
        if not devices:
            raise Exception("No devices found!")
        return devices

    def get_device_values(self, device_id, keys=None):
        """
        Retrieveing last telemotry for the device.
        If keys equals None, all values are retieved.
        """
        return self.http_get(f"/apiv2/device/{device_id}/latest")

    def get_estudna_level(self, device_id):
        """Retrieves the current value of water level(ain1)."""
        values = self.get_device_values(device_id)
        if not values or "ain1" not in values:
            return None

        try:
            # API gets list , 'value' is JSON string
            raw = values["ain1"]
            if isinstance(raw, list) and raw:
                val_str = raw[0]["value"]
                val_json = json.loads(val_str)
                return float(val_json.get("str"))  # the velue is only a number without the unnecassary other info
        except Exception as e:
            _LOGGER.error("Error while parsing the value of watter level: %s", e)
            return None
