"""
恢复脚本：添加Base → 等待摄像机自动回连 → 删除单个摄像机 → 执行完整测试
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airtest.core.api import connect_device, start_app, sleep, keyevent
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# Connect device first
connect_device('Android:///TC55LJMR59W8ZPRK')
print("[INIT] Device connected")

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

# Monkey-patch _kill_uiautomator
_orig_kill = AndroidUiautomationPoco._kill_uiautomator

def _patched_kill(self):
    import warnings
    for pkg in ("io.appium.uiautomator2.server", "com.github.uiautomator",
                 "io.appium.uiautomator2.server.test", "com.netease.open.pocoservice"):
        try:
            self.adb_client.shell(["am", "force-stop", pkg])
        except Exception:
            pass
    warnings.warn('Killed uiautomator processes via force-stop')

AndroidUiautomationPoco._kill_uiautomator = _patched_kill

from config import (
    DEVICE_SN, CAMERA_SN, PACKAGE_NAME,
    ADD_DEVICE_BTN_ID, SETTINGS_BTN_ID,
    IDENTIFIER_SCAN_QR, IDENTIFIER_ADD_POPUP,
    IDENTIFIER_DEVICE_CATEGORY, IDENTIFIER_CAMERA_KIT,
    IDENTIFIER_BASE_WIRED, IDENTIFIER_NEXT_BTN,
    IDENTIFIER_CONNECTING, IDENTIFIER_CLOUD_REGISTER,
    IDENTIFIER_DEVICE_INIT, IDENTIFIER_CONNECT_SUCCESS,
    IDENTIFIER_ADD_SUCCESS, IDENTIFIER_DELETE_BTN,
    IDENTIFIER_DELETE_CONFIRM, IDENTIFIER_UNBIND_DEVICE,
    TIMEOUT_CONNECT, TIMEOUT_SEARCH_DEVICE,
)
from poco_helpers import (
    smart_click, click_with_scroll, find_and_click_element,
    check_element_exists, pull_to_refresh, go_back_to_home,
    verify_page_transition, check_current_activity,
)

# ==================== Init Poco ====================
print("=" * 60)
print("启动App并初始化Poco...")
print("=" * 60)
start_app(PACKAGE_NAME)
sleep(5)

poco = AndroidUiautomationPoco(
    use_airtest_input=True,
    screenshot_each_action=False,
)
print("[INIT] Poco ready")

base_sn = DEVICE_SN
camera_sn = CAMERA_SN

# ==================== Step 1: Check current state ====================
print("\n" + "=" * 60)
print("步骤1：检查当前首页状态")
print("=" * 60)
sleep(2)
has_base = check_element_exists(poco, text=base_sn, timeout=5)
has_camera = check_element_exists(poco, text=camera_sn, timeout=5)
print(f"首页状态: Base={has_base}, Camera={has_camera}")

if has_base and has_camera:
    print("[STATE] Base和摄像机都在首页，直接跳到删除摄像机步骤")
elif has_base and not has_camera:
    print("[STATE] 只有Base在首页，等待摄像机回连...")
else:
    print("[STATE] Base不在首页，需要先添加Base")

# ==================== Step 2: Add Base if not present ====================
if not has_base:
    print("\n" + "=" * 60)
    print("步骤2：添加Base设备")
    print("=" * 60)

    # Ensure on home
    check_current_activity()
    for _ in range(3):
        if check_element_exists(poco, element_id=ADD_DEVICE_BTN_ID, timeout=3):
            print("[BASE-ADD] On home page")
            break
        go_back_to_home()
        sleep(2)

    # Click add button
    if not find_and_click_element(poco, ADD_DEVICE_BTN_ID, timeout=15):
        print("[ERROR] 找不到添加按钮")
        sys.exit(1)
    sleep(1)

    # Verify popup
    has_scan = check_element_exists(poco, text=IDENTIFIER_SCAN_QR, timeout=3)
    has_add = check_element_exists(poco, text=IDENTIFIER_ADD_POPUP, timeout=3)
    print(f"[BASE-ADD] Popup: 扫一扫={has_scan}, 添加设备={has_add}")

    # Click 添加设备
    if not smart_click(poco, "text", IDENTIFIER_ADD_POPUP, timeout=10):
        print("[ERROR] 点击添加设备失败")
        sys.exit(1)

    # Verify transition to device category page
    if not verify_page_transition(poco, IDENTIFIER_ADD_POPUP, IDENTIFIER_DEVICE_CATEGORY, timeout=15):
        print("[ERROR] 未跳转到选择设备类别页")
        sys.exit(1)

    # Click 摄像机套装
    sleep(0.5)
    if not click_with_scroll(poco, IDENTIFIER_CAMERA_KIT, max_scrolls=5):
        print("[ERROR] 找不到摄像机套装")
        sys.exit(1)
    sleep(1.5)

    # Click BASE(网线)
    if not click_with_scroll(poco, IDENTIFIER_BASE_WIRED, max_scrolls=5):
        print("[ERROR] 找不到BASE(网线)")
        sys.exit(1)
    sleep(0.5)

    # Click 下一步 x2
    if not smart_click(poco, "text", IDENTIFIER_NEXT_BTN, timeout=60):
        print("[ERROR] 下一步1失败")
        sys.exit(1)
    if not smart_click(poco, "text", IDENTIFIER_NEXT_BTN, timeout=60):
        print("[ERROR] 下一步2失败")
        sys.exit(1)

    # Wait for Base SN in search
    print(f"[BASE-ADD] 等待搜索到Base SN: {base_sn}...")
    try:
        element = poco(text=base_sn)
        element.wait_for_appearance(timeout=TIMEOUT_SEARCH_DEVICE)
        print(f"[BASE-ADD] 找到 {base_sn}，点击...")
        element.click()
    except Exception:
        print(f"[ERROR] 搜索超时，未找到 {base_sn}")
        sys.exit(1)

    # Wait for connection
    print("[BASE-ADD] 等待连接完成...")
    conn_start = time.time()
    conn_timeout = TIMEOUT_CONNECT
    success = False
    while time.time() - conn_start < conn_timeout:
        if check_element_exists(poco, text=IDENTIFIER_CONNECT_SUCCESS, timeout=2):
            print(f"[BASE-ADD] 连接成功 ({time.time()-conn_start:.0f}s)")
            success = True
            break
        if check_element_exists(poco, text=IDENTIFIER_ADD_SUCCESS, timeout=2):
            print(f"[BASE-ADD] 添加成功 ({time.time()-conn_start:.0f}s)")
            success = True
            break
        if check_element_exists(poco, text=IDENTIFIER_DEVICE_INIT, timeout=2):
            print(f"[BASE-ADD] 设备初始化中...")
        elif check_element_exists(poco, text=IDENTIFIER_CLOUD_REGISTER, timeout=2):
            print(f"[BASE-ADD] 注册到云端...")
        elif check_element_exists(poco, text=IDENTIFIER_CONNECTING, timeout=2):
            print(f"[BASE-ADD] 搜索设备...")
        sleep(3)

    if not success:
        print("[ERROR] Base连接超时")
        sys.exit(1)

    # Return to home
    sleep(1)
    go_back_to_home()
    sleep(2)
    has_base = check_element_exists(poco, text=base_sn, timeout=10)
    print(f"[BASE-ADD] Base在首页: {has_base}")
    if not has_base:
        print("[ERROR] Base添加后不在首页")
        sys.exit(1)

# ==================== Step 3: Wait for Camera to auto-reconnect ====================
print("\n" + "=" * 60)
print("步骤3：等待摄像机自动回连到Base")
print("=" * 60)

# Camera should auto-reconnect since it's pre-bound to Base
camera_appeared = False
wait_start = time.time()
camera_wait_timeout = 120  # 2 minutes max

while time.time() - wait_start < camera_wait_timeout:
    # Pull to refresh to trigger UI update
    pull_to_refresh(poco, times=1)
    sleep(3)

    if check_element_exists(poco, text=camera_sn, timeout=5):
        camera_appeared = True
        elapsed = time.time() - wait_start
        print(f"[CAMERA-RECONNECT] 摄像机 {camera_sn} 已出现在首页! (耗时 {elapsed:.0f}s)")
        break

    elapsed = time.time() - wait_start
    print(f"[CAMERA-RECONNECT] 等待中... ({elapsed:.0f}s / {camera_wait_timeout}s)")

if not camera_appeared:
    print(f"[WARN] 摄像机 {camera_sn} 未在 {camera_wait_timeout}s 内自动回连")
    print("[WARN] 可能摄像机未上电或不在Base附近，继续尝试...")
    # Don't exit, maybe the camera needs manual trigger
    user_input = input("摄像机未出现，是否继续？(y/n): ")
    if user_input.lower() != 'y':
        sys.exit(1)

# ==================== Step 4: Delete single camera (unbind current device) ====================
print("\n" + "=" * 60)
print("步骤4：删除单个摄像机（解绑当前设备）")
print("=" * 60)

# Click camera SN on home
if not smart_click(poco, "text", camera_sn, timeout=15):
    print(f"[ERROR] 点击摄像机 {camera_sn} 失败")
    sys.exit(1)
sleep(3)

# Dismiss popups
for dismiss_text in ["取消", "忽略", "关闭", "稍后", "暂不", "去体验"]:
    try:
        if poco(text=dismiss_text).exists():
            poco(text=dismiss_text).click()
            print(f"[DELETE] 关闭弹框: '{dismiss_text}'")
            sleep(1)
    except Exception:
        pass

# Click settings button
print("[DELETE] 点击设置按钮...")
if not find_and_click_element(poco, SETTINGS_BTN_ID, timeout=15):
    try:
        poco(name=SETTINGS_BTN_ID).click()
        sleep(2)
    except Exception as e:
        print(f"[ERROR] 点击设置按钮失败: {e}")
        sys.exit(1)
sleep(2)

# Verify settings page
settings_ok = (
    check_element_exists(poco, text="设置", timeout=3) or
    check_element_exists(poco, text="通用设置", timeout=3) or
    check_element_exists(poco, text="设备分享", timeout=3)
)
print(f"[DELETE] 设置页面确认: {settings_ok}")

# Find and click 删除设备 (at bottom, need scroll down)
if not smart_click(poco, "text", IDENTIFIER_DELETE_BTN, timeout=3):
    print("[DELETE] 直接点击删除设备失败，滚动查找...")
    if not click_with_scroll(poco, IDENTIFIER_DELETE_BTN, max_scrolls=8, scroll_direction="down"):
        print("[ERROR] 找不到删除设备")
        sys.exit(1)

# Click radio button next to 解绑当前设备 (text itself is not clickable)
sleep(1)
unbind_clicked = False
try:
    unbind_text = poco(text=IDENTIFIER_UNBIND_DEVICE)
    if unbind_text.exists():
        parent = unbind_text.parent()
        if parent.exists():
            for child in parent.children():
                try:
                    child_type = child.attr("type") or ""
                    child_text = child.attr("text") or ""
                    if child_text != IDENTIFIER_UNBIND_DEVICE and child_text != IDENTIFIER_DELETE_CONFIRM:
                        if "RadioButton" in child_type or "Image" in child_type or "CheckBox" in child_type:
                            child.click()
                            print(f"[DELETE] Clicked radio button (type={child_type}) next to 解绑当前设备")
                            unbind_clicked = True
                            break
                except Exception:
                    pass
            if not unbind_clicked:
                for child in parent.children():
                    try:
                        child_text = child.attr("text") or ""
                        if not child_text or child_text == "":
                            child.click()
                            print(f"[DELETE] Clicked empty-text sibling next to 解绑当前设备")
                            unbind_clicked = True
                            break
                    except Exception:
                        pass
except Exception as e:
    print(f"[DELETE] Error finding radio button: {e}")

if not unbind_clicked:
    print("[DELETE] 找不到解绑当前设备的圆点，尝试直接点击文字...")
    if not smart_click(poco, "text", IDENTIFIER_UNBIND_DEVICE, timeout=3):
        print("[DELETE] 尝试点击删除...")
        if not smart_click(poco, "text", IDENTIFIER_DELETE_CONFIRM, timeout=3):
            print("[ERROR] 解绑确认失败")
            sys.exit(1)

# Confirm
sleep(1)
try:
    if poco(text="确定").exists():
        poco(text="确定").click()
        print("[DELETE] 点击确定确认解绑")
except Exception:
    pass

sleep(3)

# Verify camera removed from home
camera_gone = not check_element_exists(poco, text=camera_sn, timeout=3)
print(f"[DELETE] 摄像机已从首页移除: {camera_gone}")

if not camera_gone:
    # Try pull to refresh
    for i in range(3):
        pull_to_refresh(poco, times=1)
        if not check_element_exists(poco, text=camera_sn, timeout=2):
            camera_gone = True
            break

# Also verify Base still exists
base_still_there = check_element_exists(poco, text=base_sn, timeout=5)
print(f"[DELETE] Base仍在首页: {base_still_there}")

print("\n" + "=" * 60)
if camera_gone and base_still_there:
    print("恢复完成！摄像机已单独删除，Base仍在首页。")
    print("现在可以执行完整的摄像机添加流程测试。")
else:
    print(f"恢复结果: 摄像机已删除={camera_gone}, Base仍在={base_still_there}")
print("=" * 60)
