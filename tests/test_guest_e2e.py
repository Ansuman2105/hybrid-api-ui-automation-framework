import time
from urllib import response
import pytest

from api.guest_service import GuestService
from pages.launcher_page import LauncherPage


@pytest.mark.e2e
def test_guest_api_to_ui(stb_driver):
    serial = "RPCSBLF00003505"

    # 🔥 Step 1: API call
    guest_api = GuestService()
    #data = guest_api.get_guest_details(serial)
    response = guest_api.get_guest_details(serial)
    assert response.status_code == 200
    data = response.json()

    assert data["details"], "No guest data found"

    guest = data["details"][0]

    api_checkin = guest.get("check_in_date")

    print("API CHECKIN:", api_checkin)

    # 🔥 Step 2: Wait for STB sync
    time.sleep(5)

    # 🔥 Step 3: Open launcher
    launcher = LauncherPage(stb_driver)
    launcher.wait_for_launcher()

    # 🔥 Step 4: Get UI value
    ui_value = launcher.get_guest_name_from_ui()

    print("UI VALUE:", ui_value)

    # 🔥 Step 5: Assertion
    assert ui_value is not None, "Guest not visible on UI"