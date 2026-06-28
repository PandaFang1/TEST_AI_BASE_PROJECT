"""
Base 设备添加与解绑自动化测试

完整流程（20步）：
  步骤1-13: 添加设备（搜索/连接/验证）
  步骤14-19: 删除设备（进入设置/删除/刷新验证/重试）
  步骤20:   预检查（添加前先清理已有设备）

依赖:
  - poco_helpers.py: Smart click, scroll, retry, page nav checks
  - config.py: Device SN, timeouts, identifiers
  - conftest.py: Fixtures (test_context, poco_instance, etc.)
"""
import time
import pytest
import allure

from poco_helpers import (
    smart_click, click_with_scroll, find_and_click_element,
    wait_for_text, retry_operation, check_element_exists,
    pull_to_refresh, go_back_to_home, check_current_activity,
    verify_page_transition, execute_flow_steps
)
from config import (
    DEVICE_SN, PACKAGE_NAME,
    ADD_DEVICE_BTN_ID,
    IDENTIFIER_SCAN_QR, IDENTIFIER_ADD_POPUP,
    IDENTIFIER_DEVICE_CATEGORY,
    IDENTIFIER_CAMERA_KIT, IDENTIFIER_BASE_WIRED,
    IDENTIFIER_NEXT_BTN, IDENTIFIER_CANCEL_BTN,
    IDENTIFIER_CONNECTING, IDENTIFIER_CLOUD_REGISTER,
    IDENTIFIER_DEVICE_INIT, IDENTIFIER_CONNECT_SUCCESS,
    IDENTIFIER_ADD_SUCCESS,
    IDENTIFIER_SETTINGS, IDENTIFIER_GENERAL_SETTINGS,
    IDENTIFIER_DEVICE_SHARE,
    IDENTIFIER_DELETE_BTN, IDENTIFIER_DELETE_CONFIRM,
)


@allure.epic("Base设备管理")
@allure.feature("设备添加与解绑")
@allure.story("基本操作流程")
@allure.title("Base设备添加与解绑 - 完整流程")
@allure.description(f"""
前置条件：
1. Base处于未配网状态
2. Base已插入网线
3. Android手机连接与Base相同的网络
4. 目标设备SN: {DEVICE_SN}

测试流程：
- 预检查：清理设备（若存在）
- 步骤1-13：添加设备（搜索/连接/验证）
- 步骤14-19：删除设备（设置/删除/刷新验证/重试）
""")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("P0", "冒烟测试")
@pytest.mark.p0
@pytest.mark.smoke
def test_base_device_add_and_unbind(test_context):
    """
    完整设备添加→验证→删除→验证流程
    """
    poco = test_context["poco"]
    config = test_context["config"]
    device_sn = config["device_sn"]

    # ==================== PHASE 0: Pre-check ====================
    with allure.step("预检查：检查设备是否已存在，若存在则先删除"):
        if check_element_exists(poco, text=device_sn, timeout=3):
            print(f"[PRE-CHECK] Device '{device_sn}' already exists on home, deleting first...")
            delete_result = _delete_device_flow(poco, config, device_sn)
            if not delete_result:
                pytest.fail(f"预检查失败：设备 {device_sn} 已存在于首页，删除不成功")
            print("[PRE-CHECK] Existing device deleted successfully")
        else:
            print(f"[PRE-CHECK] No existing device '{device_sn}' found. Proceeding with add.")
        check_current_activity()

    # ==================== PHASE 1: Add Device (Steps 1-13) ====================
    allure.dynamic.description(allure.dynamic.description.__func__(None)
        if hasattr(allure.dynamic.description, '__func__') else "")
    with allure.step("====== PHASE 1: 添加设备 ======"):
        add_success = _add_device_flow(poco, config, device_sn)
        assert add_success, "设备添加流程失败"

    # ==================== PHASE 2: Delete Device (Steps 14-19) ====================
    with allure.step("====== PHASE 2: 删除设备 ======"):
        for del_cycle in range(config["max_delete_retries"]):
            with allure.step(f"删除循环 {del_cycle + 1}/{config['max_delete_retries']}"):
                delete_success = _delete_device_flow(poco, config, device_sn)
                if delete_success:
                    print(f"[DELETE] Device '{device_sn}' deleted successfully on cycle {del_cycle + 1}")
                    break
                else:
                    print(f"[DELETE] Deletion cycle {del_cycle + 1} failed")
                    if del_cycle < config["max_delete_retries"] - 1:
                        print(f"[DELETE] Retrying deletion cycle {del_cycle + 2}...")
            if not delete_success and del_cycle == config["max_delete_retries"] - 1:
                pytest.fail(f"设备删除失败：经过 {config['max_delete_retries']} 次删除循环后，设备 {device_sn} 仍存在于首页")

    allure.attach("Test completed: Add + Delete + Verify all passed", name="Result",
                  attachment_type=allure.attachment_type.TEXT)


# ==================== Sub-flow: Add Device ====================
def _add_device_flow(poco, config, device_sn):
    """执行添加设备流程（步骤1-13）"""
    add_failed_steps = []

    # ---- Step 1: Click add button on home ----
    with allure.step("步骤1：首页点击添加按钮"):
        if not find_and_click_element(poco, ADD_DEVICE_BTN_ID, timeout=config["timeout"]):
            add_failed_steps.append("步骤1-点击添加按钮")
            return False
        time.sleep(1)

    # ---- Step 2: Verify popup shows "扫一扫" and "添加设备" ----
    with allure.step("步骤2：验证弹框显示「扫一扫」和「添加设备」"):
        has_scan = check_element_exists(poco, text=IDENTIFIER_SCAN_QR, timeout=3)
        has_add = check_element_exists(poco, text=IDENTIFIER_ADD_POPUP, timeout=3)
        if not (has_scan and has_add):
            allure.attach(f"扫一扫存在={has_scan}, 添加设备存在={has_add}", name="弹框验证失败",
                         attachment_type=allure.attachment_type.TEXT)
            add_failed_steps.append("步骤2-弹框验证")
            return False
        print(f"[VERIFY] Popup confirmed: 扫一扫={has_scan}, 添加设备={has_add}")

    # ---- Step 3: Click "添加设备" ----
    with allure.step("步骤3：点击「添加设备」"):
        if not smart_click(poco, "text", IDENTIFIER_ADD_POPUP, timeout=5, description="添加设备"):
            add_failed_steps.append("步骤3-点击添加设备")
            return False

    # ---- Step 3→4: Page transition check ----
    with allure.step("步骤3→4：页面跳转到选择设备类别"):
        if not verify_page_transition(poco, IDENTIFIER_ADD_POPUP, IDENTIFIER_DEVICE_CATEGORY, timeout=config["timeout"]):
            add_failed_steps.append("步骤3→4-页面跳转验证")
            return False

    # ---- Step 4-5: Find and click "摄像机套装" (with scroll) ----
    with allure.step("步骤4-5：查找并点击「摄像机套装」（支持下滑）"):
        time.sleep(0.5)
        if not click_with_scroll(poco, IDENTIFIER_CAMERA_KIT, max_scrolls=5):
            add_failed_steps.append("步骤4-5-查找摄像机套装")
            return False
        time.sleep(1.5)  # Wait for sub-options (like BASE(网线)) to expand/render

    # ---- Step 5→6: "BASE(网线)" appears, click it ----
    with allure.step("步骤6：点击「BASE(网线)」（支持下滑查找）"):
        time.sleep(1.5)  # Wait for sub-options to render after clicking 摄像机套装
        if not click_with_scroll(poco, IDENTIFIER_BASE_WIRED, max_scrolls=5):
            add_failed_steps.append("步骤6-点击BASE(网线)")
            return False
        time.sleep(0.5)

    # ---- Step 7: Wait for first "下一步" and click ----
    with allure.step("步骤7：等待第一个「下一步」可点击后点击"):
        if not smart_click(poco, "text", IDENTIFIER_NEXT_BTN, timeout=config["next_btn_timeout"], description="下一步-1"):
            add_failed_steps.append("步骤7-下一步1")
            return False

    # ---- Step 8: Wait for second "下一步" and click ----
    with allure.step("步骤8：等待第二个「下一步」可点击后点击"):
        if not smart_click(poco, "text", IDENTIFIER_NEXT_BTN, timeout=config["next_btn_timeout"], description="下一步-2"):
            add_failed_steps.append("步骤8-下一步2")
            return False

    # ---- Step 9: Wait for device SN, retry up to 3x ----
    with allure.step(f"步骤9：搜索设备SN={device_sn}（最多重试{config['max_search_retries']}次）"):
        sn_found = _wait_and_select_device_sn(poco, device_sn, config)
        if not sn_found:
            add_failed_steps.append("步骤9-搜索设备SN失败")
            return False

    # ---- Step 10: Wait for connection wizard to complete (search→register→init→done) ----
    with allure.step("步骤10：等待设备连接向导完成（搜索设备→注册到云端→设备初始化→连接成功）"):
        # After clicking SN, the wizard takes ~40-80s to complete
        # Wait for 连接成功 or 添加设备成功 to appear
        conn_start = time.time()
        conn_timeout = config["connect_timeout"]
        success_found = False
        while time.time() - conn_start < conn_timeout:
            if check_element_exists(poco, text=IDENTIFIER_CONNECT_SUCCESS, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_CONNECT_SUCCESS} appeared at {time.time()-conn_start:.0f}s")
                success_found = True
                break
            if check_element_exists(poco, text=IDENTIFIER_ADD_SUCCESS, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_ADD_SUCCESS} appeared at {time.time()-conn_start:.0f}s")
                success_found = True
                break
            # Also check for wizard progress
            if check_element_exists(poco, text=IDENTIFIER_DEVICE_INIT, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_DEVICE_INIT} in progress ({time.time()-conn_start:.0f}s)")
            elif check_element_exists(poco, text=IDENTIFIER_CLOUD_REGISTER, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_CLOUD_REGISTER} in progress ({time.time()-conn_start:.0f}s)")
            elif check_element_exists(poco, text=IDENTIFIER_CONNECTING, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_CONNECTING} in progress ({time.time()-conn_start:.0f}s)")
            time.sleep(3)
        if not success_found:
            add_failed_steps.append("步骤10-连接超时")
            return False

    # ---- Step 11: Press back to return to home ----
    with allure.step("步骤11：连接成功后按物理返回键回到首页"):
        time.sleep(1)
        go_back_to_home()
        time.sleep(2)
        print(f"[CONNECT] Connection flow completed at {time.strftime('%H:%M:%S')}")

    # ---- Step 12: Verify device appears on home page ----
    with allure.step("步骤12：验证设备SN出现在首页"):
        time.sleep(1)
        device_on_page = check_element_exists(poco, text=device_sn, timeout=config["timeout"])
        if not device_on_page:
            allure.attach(f"Device {device_sn} not found on home", name="首页验证失败",
                         attachment_type=allure.attachment_type.TEXT)
            add_failed_steps.append("步骤12-首页验证设备")
            return False
        print(f"[VERIFY] Device '{device_sn}' confirmed on home screen")

    # ---- Step 13: Pairing success determination ----
    with allure.step("步骤13：判定配网成功"):
        print(f"[RESULT] Pairing SUCCESS: Device '{device_sn}' connected and visible on home")
        allure.attach(f"Device {device_sn} paired successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                     name="配网结果", attachment_type=allure.attachment_type.TEXT)

    return True


# ==================== Sub-flow: Delete Device ====================
def _delete_device_flow(poco, config, device_sn):
    """执行删除设备流程（步骤14-19），返回True=成功删除"""
    del_failed_steps = []

    # ---- Step 14: Click device SN on home ----
    with allure.step(f"步骤14：首页点击设备SN「{device_sn}」"):
        if not smart_click(poco, "text", device_sn, timeout=config["timeout"], description=f"device SN={device_sn}"):
            del_failed_steps.append("步骤14-点击设备SN")
            return False

    # ---- Step 15: Wait for settings page ----
    with allure.step("步骤15：等待进入设备设置页面"):
        time.sleep(3)
        # Verify we're on settings page by checking for any recognizable element
        page_ok = (
            check_element_exists(poco, text=IDENTIFIER_DELETE_BTN, timeout=config["timeout"]) or
            check_element_exists(poco, text=IDENTIFIER_SETTINGS, timeout=3) or
            check_element_exists(poco, text=IDENTIFIER_GENERAL_SETTINGS, timeout=3) or
            check_element_exists(poco, text=IDENTIFIER_DEVICE_SHARE, timeout=3)
        )
        if not page_ok:
            del_failed_steps.append("步骤15-进入设备设置页")
            return False
        print("[VERIFY] Device settings page loaded")

    # ---- Step 16: Click delete button ----
    with allure.step("步骤16：点击「删除设备」按钮"):
        if not smart_click(poco, "text", IDENTIFIER_DELETE_BTN, timeout=config["timeout"], description="删除设备"):
            del_failed_steps.append("步骤16-点击删除设备")
            return False

    # ---- Step 17: Confirm delete in popup ----
    with allure.step("步骤17：弹框中确认删除"):
        if not smart_click(poco, "text", IDENTIFIER_DELETE_CONFIRM, timeout=5, description="确认删除"):
            del_failed_steps.append("步骤17-确认删除")
            return False

    # ---- Step 18: Back to home and verify device removed ----
    with allure.step("步骤18：返回首页，检查SN是否还存在（存在则下拉刷新3次）"):
        time.sleep(3)  # Wait for auto-navigation back to home
        device_removed = _verify_device_removed(poco, device_sn, config["refresh_count_on_delete"])
        if not device_removed:
            allure.attach(f"Device {device_sn} still on home after delete + {config['refresh_count_on_delete']} refreshes",
                         name="删除验证失败", attachment_type=allure.attachment_type.TEXT)
            return False

    print(f"[RESULT] Device '{device_sn}' successfully removed from home")
    return True


# ==================== Helper: Wait for SN in search ====================
def _wait_and_select_device_sn(poco, device_sn, config):
    """
    Wait for target device SN to appear in search results.
    Retry up to MAX_SEARCH_RETRIES times. Record search time per attempt.
    """
    for attempt in range(config["max_search_retries"]):
        search_start = time.time()
        with allure.step(f"搜索尝试 {attempt + 1}/{config['max_search_retries']}: 等待SN={device_sn}"):
            try:
                element = poco(text=device_sn)
                element.wait_for_appearance(timeout=config["search_timeout"])
                elapsed = time.time() - search_start
                allure.attach(f"Search took {elapsed:.1f}s on attempt {attempt + 1}", name="搜索耗时",
                             attachment_type=allure.attachment_type.TEXT)
                print(f"[SEARCH] Found '{device_sn}' in {elapsed:.1f}s (attempt {attempt + 1})")
                element.click()
                return True
            except Exception:
                elapsed = time.time() - search_start
                print(f"[SEARCH] Timeout after {elapsed:.1f}s, SN '{device_sn}' not found (attempt {attempt + 1})")
                allure.attach(f"Search timeout: {elapsed:.1f}s", name=f"搜索超时-尝试{attempt + 1}",
                             attachment_type=allure.attachment_type.TEXT)

                # Cancel and retry
                if attempt < config["max_search_retries"] - 1:
                    try:
                        poco(text=IDENTIFIER_CANCEL_BTN).click()
                        time.sleep(2)
                    except Exception:
                        print("[SEARCH] Could not click cancel button")

    print(f"[SEARCH] FAILED: Could not find '{device_sn}' after {config['max_search_retries']} attempts")
    return False


# ==================== Helper: Verify device removed ====================
def _verify_device_removed(poco, device_sn, max_refresh=3):
    """
    Check home screen for device SN. If still present, pull-to-refresh and recheck.
    """
    for refresh_attempt in range(max_refresh):
        # Wait between checks to allow page to settle
        if refresh_attempt > 0:
            time.sleep(2)
        exists = check_element_exists(poco, text=device_sn, timeout=3)
        if not exists:
            print(f"[VERIFY] Device '{device_sn}' successfully removed (refresh {refresh_attempt})")
            return True
        print(f"[VERIFY] Device '{device_sn}' still present after delete, refresh {refresh_attempt + 1}/{max_refresh}")
        pull_to_refresh(poco, times=1)

    print(f"[VERIFY] Device '{device_sn}' still exists after {max_refresh} refreshes")
    return False
