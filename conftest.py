"""
conftest.py - Shared fixtures and Allure configuration for Base device tests.

Fixtures:
    global_config  (session) - Test config from config.py
    app_foreground (function) - Ensure SmartEye app is in foreground
    poco_instance  (function) - Fresh Poco instance per test
    test_context   (function) - Aggregated fixture {poco, config}
"""
import pytest
import allure
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==================== Allure Environment ====================
def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: Smoke tests")
    config.addinivalue_line("markers", "p0: Priority 0 critical tests")
    config.addinivalue_line("markers", "p1: Priority 1 important tests")
    config.addinivalue_line("markers", "p2: Priority 2 normal tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "regression: Regression tests")

    os.makedirs("allure-results", exist_ok=True)
    with open("allure-results/environment.properties", "w") as f:
        f.write(f"Python={os.sys.version}\n")
        f.write(f"Pytest={pytest.__version__}\n")
        f.write(f"Timestamp={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"DeviceID=TC55LJMR59W8ZPRK\n")
        f.write(f"App=com.cloudedge.smarteye\n")
        f.write(f"DeviceSN=129653415\n")


# ==================== Setup / Teardown ====================
@pytest.fixture(scope="session")
def global_config():
    from config import (
        DEVICE_SN, PACKAGE_NAME, TIMEOUT_CLICK, TIMEOUT_SEARCH_DEVICE,
        TIMEOUT_CONNECT, MAX_SEARCH_RETRIES, MAX_DELETE_RETRIES,
        REFRESH_COUNT_ON_DELETE, RETRY_DELAY, TIMEOUT_NEXT_BTN
    )
    config = {
        "device_sn": DEVICE_SN,
        "package_name": PACKAGE_NAME,
        "timeout": TIMEOUT_CLICK,
        "next_btn_timeout": TIMEOUT_NEXT_BTN,
        "search_timeout": TIMEOUT_SEARCH_DEVICE,
        "connect_timeout": TIMEOUT_CONNECT,
        "max_search_retries": MAX_SEARCH_RETRIES,
        "max_delete_retries": MAX_DELETE_RETRIES,
        "refresh_count_on_delete": REFRESH_COUNT_ON_DELETE,
        "retry_delay": RETRY_DELAY,
    }
    yield config


@pytest.fixture(scope="function")
def app_foreground(global_config):
    """Ensure SmartEye app is in foreground before each test."""
    from airtest.core.api import start_app, sleep
    package = global_config["package_name"]

    # Try to bring app to foreground without killing it
    try:
        start_app(package)
    except Exception:
        pass
    sleep(3)
    yield
    # Teardown: do nothing - app stays on its home (device list) page
    # The test itself already navigates back to app home after each operation


@pytest.fixture(scope="function")
def poco_instance():
    """Provide a fresh Poco instance per test function."""
    # Monkey-patch to suppress uiautomator uninstall error
    from poco.drivers.android.utils import installation
    _orig_uninstall = installation.uninstall

    def _safe_uninstall(adb_client, package_name):
        try:
            _orig_uninstall(adb_client, package_name)
        except Exception as e:
            import warnings
            warnings.warn(f"Ignored uninstall error for {package_name}: {e}")

    installation.uninstall = _safe_uninstall

    # Also monkey-patch _kill_uiautomator to use force-stop instead of kill+uninstall
    from poco.drivers.android.uiautomation import AndroidUiautomationPoco
    _orig_kill = AndroidUiautomationPoco._kill_uiautomator

    def _patched_kill(self):
        # Use am force-stop for all uiautomator-related packages (no root needed)
        import warnings
        for pkg in ("io.appium.uiautomator2.server", "com.github.uiautomator",
                     "io.appium.uiautomator2.server.test", "com.netease.open.pocoservice"):
            try:
                self.adb_client.shell(["am", "force-stop", pkg])
            except Exception:
                pass
        warnings.warn('Killed uiautomator processes via force-stop')

    AndroidUiautomationPoco._kill_uiautomator = _patched_kill

    poco = AndroidUiautomationPoco(
        use_airtest_input=True,
        screenshot_each_action=False,
    )

    yield poco

    # Restore originals
    installation.uninstall = _orig_uninstall
    AndroidUiautomationPoco._kill_uiautomator = _orig_kill


# ==================== Allure Failure Screenshot Hook ====================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        try:
            from airtest.core.api import snapshot
            import allure
            path = os.path.join("allure-results", f"failure_{item.name}_{int(time.time())}.png")
            snapshot(msg=path)
            allure.attach.file(path, name="Failure Screenshot",
                               attachment_type=allure.attachment_type.PNG)
        except Exception as e:
            allure.attach(str(e), name="Screenshot Error",
                          attachment_type=allure.attachment_type.TEXT)


# ==================== Aggregated Fixture ====================
@pytest.fixture(scope="function")
def test_context(poco_instance, app_foreground, global_config):
    """Aggregate all test dependencies into a single context dict."""
    return {
        "poco": poco_instance,
        "config": global_config,
    }
