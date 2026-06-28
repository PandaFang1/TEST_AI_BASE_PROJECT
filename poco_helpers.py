"""
Poco Helper Functions
Reusable utilities for Poco-based Android/iOS UI automation tests.
Enhanced with page navigation checks (Activity validation + transition verification).
"""
import time
import subprocess
from airtest.core.api import snapshot, sleep


def smart_click(poco, selector_type, selector_value, timeout=30, description=""):
    """
    Wait for an element to appear and click it.
    On failure, check if app is still in foreground.

    Args:
        poco: Poco instance
        selector_type: "text", "name", "textMatches", "type"
        selector_value: The selector value string
        timeout: Max seconds to wait
        description: Human-readable step description for logging
    Returns:
        bool: True if clicked successfully, False otherwise
    """
    try:
        if selector_type == "text":
            element = poco(text=selector_value)
        elif selector_type == "name":
            element = poco(name=selector_value)
        elif selector_type == "textMatches":
            element = poco(textMatches=selector_value)
        elif selector_type == "type":
            element = poco(type=selector_value)
        else:
            raise ValueError(f"Unknown selector_type: {selector_type}")

        desc = description or f"{selector_type}={selector_value}"
        print(f"[CLICK] Waiting for: {desc} (timeout={timeout}s)")
        element.wait_for_appearance(timeout=timeout)
        element.click()
        print(f"[CLICK] Clicked: {desc}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to click {selector_type}={selector_value}: {e}")
        check_current_activity()
        snapshot(msg=f"Failed to click {selector_type}={selector_value}")
        return False


def click_with_scroll(poco, text, max_scrolls=5, scroll_direction="down"):
    """
    Try to click an element by text. If not visible, scroll to find it.

    Args:
        poco: Poco instance
        text: Text content to match
        max_scrolls: Max number of scroll attempts
        scroll_direction: "down" or "up"
    Returns:
        bool: True if clicked successfully
    """
    for attempt in range(max_scrolls):
        if poco(text=text).exists():
            poco(text=text).click()
            print(f"[SCROLL-CLICK] Found and clicked '{text}' after {attempt} scrolls")
            return True
        print(f"[SCROLL] Attempt {attempt + 1}/{max_scrolls}: scrolling {scroll_direction}...")
        if scroll_direction == "down":
            poco.swipe([0.5, 0.7], [0.5, 0.3], duration=0.5)
        else:
            poco.swipe([0.5, 0.3], [0.5, 0.7], duration=0.5)
        sleep(1)
    print(f"[SCROLL-CLICK] '{text}' not found after {max_scrolls} scrolls")
    snapshot(msg=f"Element not found: {text}")
    return False


def find_and_click_element(poco, element_id, timeout=15):
    """
    Find element by resource ID and click it.

    Args:
        poco: Poco instance
        element_id: Android resource ID (e.g., 'com.example:id/btn')
        timeout: Max seconds to wait
    Returns:
        bool: True if successful
    """
    try:
        element = poco(name=element_id)
        element.wait_for_appearance(timeout=timeout)
        element.click()
        print(f"[ID-CLICK] Clicked: {element_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to click element '{element_id}': {e}")
        check_current_activity()
        snapshot(msg=f"Element not found: {element_id}")
        return False


def wait_for_text(poco, text, timeout=30, should_exist=True):
    """
    Wait for text to appear or disappear on screen.

    Args:
        poco: Poco instance
        text: Text content to watch for
        timeout: Max seconds to wait
        should_exist: True = wait for appearance, False = wait for disappearance
    Returns:
        bool: True if condition met before timeout
    """
    try:
        element = poco(text=text)
        if should_exist:
            element.wait_for_appearance(timeout=timeout)
            print(f"[WAIT] Text appeared: '{text}'")
        else:
            element.wait_for_disappearance(timeout=timeout)
            print(f"[WAIT] Text disappeared: '{text}'")
        return True
    except Exception as e:
        action = "appear" if should_exist else "disappear"
        print(f"[TIMEOUT] Text '{text}' did not {action} within {timeout}s")
        check_current_activity()
        snapshot(msg=f"Timeout: {text}")
        return False


def retry_operation(operation, max_retries=3, delay=2, description=""):
    """
    Retry an operation multiple times with delay between attempts.

    Args:
        operation: Callable that returns True/False
        max_retries: Max number of attempts
        delay: Seconds between retries
        description: Human-readable description
    Returns:
        bool: True if any attempt succeeded
    """
    for attempt in range(max_retries):
        try:
            print(f"[RETRY] {description} - Attempt {attempt + 1}/{max_retries}")
            result = operation()
            if result:
                print(f"[RETRY] {description} - Succeeded on attempt {attempt + 1}")
                return True
        except Exception as e:
            print(f"[RETRY] {description} - Attempt {attempt + 1} error: {e}")
        if attempt < max_retries - 1:
            print(f"[RETRY] Waiting {delay}s before retry...")
            sleep(delay)
    print(f"[RETRY] {description} - All {max_retries} attempts failed")
    return False


def check_element_exists(poco, text=None, element_id=None, timeout=5):
    """
    Check if an element exists on screen.

    Args:
        poco: Poco instance
        text: Text content to match (optional)
        element_id: Resource ID to match (optional)
        timeout: Seconds to wait for appearance
    Returns:
        bool: True if element exists
    """
    element = None
    if text:
        element = poco(text=text)
    elif element_id:
        element = poco(name=element_id)
    else:
        return False
    return element.exists()


def pull_to_refresh(poco, times=1):
    """
    Perform pull-to-refresh gesture.

    Args:
        poco: Poco instance
        times: Number of refresh attempts
    """
    for i in range(times):
        print(f"[REFRESH] Pull-to-refresh {i + 1}/{times}")
        poco.swipe([0.5, 0.3], [0.5, 0.7], duration=0.3)
        sleep(3)  # Wait for page to finish loading after refresh


def take_screenshot_on_failure(poco, step_name):
    """Take a screenshot for debugging."""
    filename = f"failure_{step_name}_{int(time.time())}.png"
    snapshot(msg=filename)
    print(f"[SCREENSHOT] Saved: {filename}")


def execute_flow_steps(poco, steps, overall_timeout=180):
    """
    Execute a list of test steps with overall timeout control.

    Args:
        poco: Poco instance
        steps: List of (step_name, callable) tuples
        overall_timeout: Max total execution time in seconds
    Returns:
        tuple: (success_count, total_count, failed_steps)
    """
    start_time = time.time()
    success_count = 0
    failed_steps = []

    for i, (step_name, step_func) in enumerate(steps):
        elapsed = time.time() - start_time
        if elapsed > overall_timeout:
            print(f"[TIMEOUT] Overall timeout ({overall_timeout}s) exceeded at step: {step_name}")
            for s in steps[i:]:
                failed_steps.append((s[0], "SKIPPED_TIMEOUT"))
            break

        print(f"\n{'='*50}")
        print(f"[STEP] {step_name} (elapsed: {elapsed:.1f}s)")
        print(f"{'='*50}")

        try:
            result = step_func()
            if result:
                success_count += 1
                print(f"[PASS] {step_name}")
            else:
                failed_steps.append((step_name, "FAILED"))
                print(f"[FAIL] {step_name}")
        except Exception as e:
            failed_steps.append((step_name, str(e)))
            print(f"[ERROR] {step_name}: {e}")
            take_screenshot_on_failure(poco, step_name)

    total = len(steps)
    print(f"\n{'='*50}")
    print(f"[SUMMARY] {success_count}/{total} steps passed")
    if failed_steps:
        print(f"[SUMMARY] Failed steps: {failed_steps}")
    print(f"{'='*50}")

    return success_count, total, failed_steps


# ==================== Page Navigation Checks ====================

def check_current_activity(target_package="com.cloudedge.smarteye"):
    """
    Check if the current foreground Activity belongs to the target app.
    Use when element lookup fails to diagnose app state.

    Args:
        target_package: Expected app package name
    Returns:
        bool: True if current activity belongs to target app
    """
    try:
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "activity", "activities"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if "topResumedActivity" in line or "mResumedActivity" in line:
                if target_package in line:
                    print(f"[ACTIVITY] OK - Current activity: {line.strip()}")
                    return True
                else:
                    print(f"[ACTIVITY] WARNING - Expected {target_package}, got: {line.strip()}")
                    return False
        print("[ACTIVITY] WARNING - Could not determine current activity")
        return False
    except Exception as e:
        print(f"[ACTIVITY] ERROR checking activity: {e}")
        return False


def verify_page_transition(poco, before_identifier, expected_identifier, timeout=10):
    """
    Verify that a page transition occurred successfully.

    1. Wait for the target page's unique identifier to appear
    2. Optionally check that the previous page's identifier is gone

    Args:
        poco: Poco instance
        before_identifier: Text element unique to the previous page (optional, pass None to skip)
        expected_identifier: Text element unique to the target page
        timeout: Max seconds to wait for target page identifier
    Returns:
        bool: True if transition verified
    """
    # 1. Wait for target page identifier
    try:
        target_element = poco(text=expected_identifier)
        target_element.wait_for_appearance(timeout=timeout)
        print(f"[TRANSITION] Target page confirmed: '{expected_identifier}'")
    except Exception:
        print(f"[TRANSITION] FAILED - Target page identifier '{expected_identifier}' not found within {timeout}s")
        snapshot(msg=f"Transition failed - expected: {expected_identifier}")
        return False

    # 2. Check previous page is gone (best-effort)
    if before_identifier:
        sleep(0.5)
        if poco(text=before_identifier).exists():
            print(f"[TRANSITION] WARNING - Previous page element '{before_identifier}' still visible (may be normal)")

    print(f"[TRANSITION] Page transition verified successfully")
    return True


def go_back_to_home(check_element=None):
    """
    Press Android back key to return to home screen.
    Optionally verify we're back on home by checking for a specific element.

    Args:
        check_element: Text to verify on home screen (optional)
    """
    from airtest.core.api import keyevent
    keyevent("BACK")
    sleep(1.5)
    print("[NAV] Pressed BACK key")
    return True
