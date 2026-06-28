"""
Loop test: Camera add → verify → delete → verify, run 5 times.
Each run starts from home page. If camera already exists, delete it first.
"""
import sys
import time
import traceback
import subprocess
import re

from airtest.core.api import connect_device, start_app, sleep, keyevent
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

connect_device('Android:///TC55LJMR59W8ZPRK')
start_app("com.cloudedge.smarteye")
sleep(5)
poco = AndroidUiautomationPoco()
print("[INIT] Ready")

from test_cases.test_camera_add_unbind import (
    _add_camera_flow,
    _verify_camera_in_sub_device,
    _verify_camera_streaming,
    _verify_camera_bind_to_base,
    _delete_camera_flow,
)
from config import DEVICE_SN, CAMERA_SN, ADD_DEVICE_BTN_ID
from poco_helpers import check_element_exists, go_back_to_home, smart_click

BASE_SN = DEVICE_SN
CAM_SN = CAMERA_SN

config = {
    "max_delete_retries": 3,
    "max_search_retries": 3,
    "search_timeout": 90,
    "connect_timeout": 120,
    "timeout": 15,
    "stream_timeout": 60,
    "refresh_count_on_delete": 3,
    "next_btn_timeout": 60,
}

TOTAL = 5
results = []


def ensure_home():
    """Press BACK until we see the add button on home, or restart app."""
    for _ in range(8):
        if check_element_exists(poco, element_id=ADD_DEVICE_BTN_ID, timeout=3):
            print("[HOME] On home page")
            return True
        keyevent("BACK")
        sleep(2)
    start_app("com.cloudedge.smarteye")
    sleep(5)
    if check_element_exists(poco, element_id=ADD_DEVICE_BTN_ID, timeout=5):
        print("[HOME] On home page (after restart)")
        return True
    print("[HOME] FAILED to reach home page")
    return False


def ensure_full_home():
    """Aggressively return to home page by pressing BACK multiple times + restart if needed."""
    # First try BACK keys
    for _ in range(8):
        try:
            if check_element_exists(poco, element_id=ADD_DEVICE_BTN_ID, timeout=2):
                print("[FULL-HOME] On home page")
                sleep(1)
                return True
        except Exception:
            pass
        keyevent("BACK")
        sleep(2)
    # If still not home, restart app
    print("[FULL-HOME] Restarting app...")
    start_app("com.cloudedge.smarteye")
    sleep(6)
    try:
        if check_element_exists(poco, element_id=ADD_DEVICE_BTN_ID, timeout=8):
            print("[FULL-HOME] On home page (after restart)")
            sleep(1)
            return True
    except Exception:
        pass
    print("[FULL-HOME] FAILED to reach home page")
    return False


def click_camera_on_home(camera_sn):
    """Click camera SN on home page using resource-id for precise targeting."""
    try:
        # Find the camera name element by resource-id
        cam_element = poco(name="com.cloudedge.smarteye:id/tvCameraName", text=camera_sn)
        if not cam_element.exists():
            print(f"[CAM-CLICK] Camera '{camera_sn}' text not found via resource-id")
            return False
        # Get its parent (clickable container)
        parent = cam_element.parent()
        if parent is None:
            print(f"[CAM-CLICK] Camera parent is None, trying direct click")
            cam_element.click()
        else:
            print(f"[CAM-CLICK] Clicking camera parent container")
            parent.click()
        sleep(2)
        print(f"[CAM-CLICK] Clicked camera '{camera_sn}'")
        return True
    except Exception as e:
        print(f"[CAM-CLICK] Error clicking camera: {e}")
        # Fallback: try text-based click
        try:
            if poco(text=camera_sn).exists():
                poco(text=camera_sn).click()
                sleep(2)
                print(f"[CAM-CLICK] Fallback text click on '{camera_sn}'")
                return True
        except Exception as e2:
            print(f"[CAM-CLICK] Fallback also failed: {e2}")
        return False


def click_base_on_home(base_sn):
    """Click Base SN on home page using resource-id for precise targeting."""
    try:
        # Find the Base name element by resource-id
        base_element = poco(name="com.cloudedge.smarteye:id/tvNvrNeutralName", text=base_sn)
        if not base_element.exists():
            print(f"[BASE-CLICK] Base '{base_sn}' not found via resource-id")
            return False
        # Get its parent (clickable container)
        parent = base_element.parent()
        if parent is None:
            print(f"[BASE-CLICK] Base parent is None, trying direct click")
            base_element.click()
        else:
            # Try to go up to the clickable ancestor
            grandparent = parent.parent()
            if grandparent is not None:
                print(f"[BASE-CLICK] Clicking Base grandparent container")
                grandparent.click()
            else:
                print(f"[BASE-CLICK] Clicking Base parent container")
                parent.click()
        sleep(2)
        print(f"[BASE-CLICK] Clicked Base '{base_sn}'")
        return True
    except Exception as e:
        print(f"[BASE-CLICK] Error clicking Base: {e}")
        # Fallback: try text-based click
        try:
            if poco(text=base_sn).exists():
                poco(text=base_sn).click()
                sleep(2)
                print(f"[BASE-CLICK] Fallback text click on '{base_sn}'")
                return True
        except Exception as e2:
            print(f"[BASE-CLICK] Fallback also failed: {e2}")
        return False


def verify_camera_in_sub_device_v2(poco, config, base_sn, camera_sn):
    """
    Enhanced version: uses precise Base click, then verifies camera in sub-device mgmt.
    """
    print(f"[SUB-VERIFY] Entering Base sub-device management...")

    # Click Base on home using precise method
    if not click_base_on_home(base_sn):
        print("[SUB-VERIFY] Failed to click Base on home")
        return False
    sleep(3)

    # Verify we're on Base settings page
    from config import IDENTIFIER_GENERAL_SETTINGS, IDENTIFIER_SUB_DEVICE_MGMT
    if not check_element_exists(poco, text=IDENTIFIER_GENERAL_SETTINGS, timeout=10):
        print("[SUB-VERIFY] Not on Base settings page (通用设置 not found)")
        # Try BACK and retry
        keyevent("BACK")
        sleep(2)
        if not ensure_home():
            return False
        if not click_base_on_home(base_sn):
            return False
        sleep(3)
        if not check_element_exists(poco, text=IDENTIFIER_GENERAL_SETTINGS, timeout=10):
            print("[SUB-VERIFY] Still not on Base settings page after retry")
            return False

    print("[SUB-VERIFY] On Base settings page")

    # Click 通用设置
    if not smart_click(poco, "text", IDENTIFIER_GENERAL_SETTINGS, timeout=10, description="通用设置"):
        print("[SUB-VERIFY] Failed to click 通用设置")
        return False
    sleep(1)

    # Click 子设备管理
    if not smart_click(poco, "text", IDENTIFIER_SUB_DEVICE_MGMT, timeout=10, description="子设备管理"):
        print("[SUB-VERIFY] Failed to click 子设备管理")
        return False
    sleep(2)

    # Check camera SN in sub-device management
    camera_found = check_element_exists(poco, text=camera_sn, timeout=10)
    if not camera_found:
        print(f"[SUB-VERIFY] Camera '{camera_sn}' NOT found in sub-device management")
        return False

    print(f"[SUB-VERIFY] Camera '{camera_sn}' found in sub-device management")
    return True


def verify_camera_streaming_v2(poco, config, camera_sn):
    """
    Enhanced version: ensures we're on home page, then clicks camera using precise method.
    """
    print(f"[STREAM-VERIFY] Verifying camera streaming...")

    # Ensure we're on home page first
    if not ensure_full_home():
        print("[STREAM-VERIFY] Cannot reach home page")
        return False

    # Click camera using precise method
    if not click_camera_on_home(camera_sn):
        print("[STREAM-VERIFY] Failed to click camera on home")
        return False

    # Dismiss any popups
    sleep(2)
    for dismiss_text in ["取消", "忽略", "关闭", "稍后", "暂不"]:
        try:
            if poco(text=dismiss_text).exists():
                poco(text=dismiss_text).click()
                print(f"[STREAM-VERIFY] Dismissed popup: '{dismiss_text}'")
                sleep(1)
        except Exception:
            pass

    # Wait for streaming (electricity icon)
    ELECTRICITY_ICON_ID = "com.cloudedge.smarteye:id/iv_electricity"
    stream_start = time.time()
    stream_timeout = config.get("stream_timeout", 60)
    electricity_found = False

    while time.time() - stream_start < stream_timeout:
        if check_element_exists(poco, element_id=ELECTRICITY_ICON_ID, timeout=2):
            if not electricity_found:
                print(f"[STREAM-VERIFY] Electricity icon appeared at {time.time()-stream_start:.0f}s, waiting 5s...")
                electricity_found = True
                electricity_time = time.time()
            if electricity_found and time.time() - electricity_time >= 5:
                print(f"[STREAM-VERIFY] Camera streaming stable for 5s confirmed")
                break
        elif electricity_found:
            print(f"[STREAM-VERIFY] WARNING: Electricity icon disappeared, re-waiting...")
            electricity_found = False
        sleep(2)

    if not electricity_found:
        print("[STREAM-VERIFY] Camera streaming timeout")
        return False

    print(f"[STREAM-VERIFY] Camera streaming verified")
    return True


# ==================== MAIN LOOP ====================
for run in range(1, TOTAL + 1):
    print(f"\n{'#'*60}")
    print(f"###### RUN {run}/{TOTAL} ######")
    print(f"{'#'*60}")
    t0 = time.time()
    ok = False

    try:
        # ===== Step A: Ensure we are on home page =====
        if not ensure_home():
            results.append((run, False, "Cannot reach home"))
            continue
        sleep(1)

        # ===== Step B: Check if camera already exists on home, delete it first =====
        has_camera = check_element_exists(poco, text=CAM_SN, timeout=5)
        if has_camera:
            print(f"[RUN{run}] Camera already on home, deleting first...")
            for cycle in range(3):
                if _delete_camera_flow(poco, config, CAM_SN, base_sn=BASE_SN):
                    print(f"[RUN{run}] Existing camera deleted (cycle {cycle+1})")
                    break
                sleep(2)
            else:
                print(f"[RUN{run}] WARNING: Could not delete existing camera, proceeding anyway")
            # Go back to home after delete
            ensure_home()
            sleep(1)

        # ===== Step C: Verify Base is on home =====
        if not check_element_exists(poco, text=BASE_SN, timeout=5):
            print(f"[RUN{run}] ERROR: Base not on home!")
            results.append((run, False, "Base missing"))
            continue
        print(f"[RUN{run}] Pre-check OK: Base={BASE_SN}, Camera not on home")

        # ===== Phase 1: Add Camera =====
        print(f"[RUN{run}] Phase 1: Adding camera...")
        t1 = time.time()
        if not _add_camera_flow(poco, config, BASE_SN, CAM_SN):
            print(f"[RUN{run}] FAIL at Phase 1 (add camera)")
            results.append((run, False, "Add camera failed"))
            continue
        print(f"[RUN{run}] Camera added ({time.time()-t1:.0f}s)")

        # ===== Phase 2: Verify in sub-device (using enhanced v2) =====
        print(f"[RUN{run}] Phase 2: Verifying in sub-device management...")
        # First ensure we're on home page after add flow
        if not ensure_home():
            print(f"[RUN{run}] Cannot reach home after add, but continuing...")
            sleep(2)
        if not verify_camera_in_sub_device_v2(poco, config, BASE_SN, CAM_SN):
            print(f"[RUN{run}] FAIL at Phase 2 (sub-device verify)")
            results.append((run, False, "Sub-device verify failed"))
            continue
        print(f"[RUN{run}] Sub-device verify OK")

        # ===== Phase 3: Verify streaming (using enhanced v2) =====
        print(f"[RUN{run}] Phase 3: Verifying camera streaming...")
        if not verify_camera_streaming_v2(poco, config, CAM_SN):
            print(f"[RUN{run}] FAIL at Phase 3 (streaming)")
            results.append((run, False, "Streaming failed"))
            continue
        print(f"[RUN{run}] Streaming OK")

        # Combined add-success check
        base_ok = check_element_exists(poco, text=BASE_SN, timeout=5)
        print(f"[RUN{run}] Add success: sub-device=OK, streaming=OK, base={base_ok}")

        # ===== Phase 4: Verify bind (MUST be on camera preview page from Phase 3) =====
        print(f"[RUN{run}] Phase 4: Verifying camera bind to Base...")
        # NOTE: Do NOT go home here! Phase 3 ends on the camera preview/live view page.
        # _verify_camera_bind_to_base clicks the settings button on that page.
        if not _verify_camera_bind_to_base(poco, config, BASE_SN):
            print(f"[RUN{run}] FAIL at Phase 4 (bind verify)")
            results.append((run, False, "Bind verify failed"))
            continue
        print(f"[RUN{run}] Bind verify OK")

        # ===== Phase 5: Delete camera (need to be on home page first) =====
        print(f"[RUN{run}] Phase 5: Deleting camera...")
        # Phase 4 ends on device info page, need to go back to home
        if not ensure_home():
            print(f"[RUN{run}] WARNING: Cannot reach home before delete")
        sleep(1)
        for cycle in range(3):
            if _delete_camera_flow(poco, config, CAM_SN, base_sn=BASE_SN):
                print(f"[RUN{run}] Camera deleted (cycle {cycle+1})")
                ok = True
                break
            print(f"[RUN{run}] Delete cycle {cycle+1} failed, retry...")
            ensure_home()
            sleep(1)

        if not ok:
            print(f"[RUN{run}] FAIL at Phase 5 (delete)")
            results.append((run, False, "Delete failed"))
            continue

        elapsed = time.time() - t0
        print(f"[RUN{run}] PASS ({elapsed:.0f}s)")
        results.append((run, True, f"{elapsed:.0f}s"))

    except Exception as e:
        print(f"[RUN{run}] EXCEPTION: {e}")
        traceback.print_exc()
        results.append((run, False, str(e)[:80]))

# ---- Summary ----
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
passed = sum(1 for _, ok, _ in results if ok)
for r, ok, note in results:
    status = "PASS" if ok else "FAIL"
    print(f"  Run {r}: {status} ({note})")
print(f"\nResult: {passed}/{TOTAL} passed")
