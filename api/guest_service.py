import requests
from utils.logger import get_logger

log = get_logger(__name__)


class GuestService:

    BASE_URL   = "https://devices.cms.jio.com"
    ENDPOINT   = "/jiohotels/v2/stb/get_guest_details"
    TOKEN      = "1a0ffdd9877d3948443bd195502838c8"  # raw token — no "Bearer" prefix

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.TOKEN,   # Jio Hotels API: raw token, NOT "Bearer <token>"
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        })

    def get_guest_details(self, serial_num: str) -> requests.Response:
        log.info("Fetching guest details: serial=%s", serial_num)

        response = self.session.get(
            f"{self.BASE_URL}{self.ENDPOINT}",
            params={"serial_num": serial_num},
            timeout=30,
        )

        log.debug("Status: %s  Body: %s", response.status_code, response.text[:200])
        return response