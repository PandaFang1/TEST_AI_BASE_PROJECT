"""
摄像机（子设备）添加与解绑自动化测试

完整流程：
  步骤1-3:   添加Base设备（同Base流程前三步：首页→添加按钮→弹框→添加设备→选择设备类别→摄像机套装→BASE）
  步骤4-6:   搜索并添加摄像机（搜索SN→点击子设备摄像机SN→添加至Base/NVR→连接等待）
  步骤7:     返回首页
  步骤8-10:  进入Base子设备管理验证摄像机（点击Base SN→通用设置→子设备管理→检查摄像机SN）
  步骤11-12: 进入摄像机查看出流（返回首页→点击摄像机SN→忽略弹框→等待出流5秒）
  步骤13-14: 验证摄像机绑定Base（点击设置按钮→设备信息→检查WiFi名称为Base SN）
  步骤15-17: 删除摄像机（返回设置页→下滑找删除设备→解绑当前设备→返回首页）
  步骤18-19: 验证摄像机删除（再次进子设备管理→检查无摄像机SN）

子设备摄像机添加成功判定标准：
  步骤8（Base设置页可进入 + 子设备管理中摄像机SN存在）
  + 步骤12（摄像机出流正常，电量图标持续5秒）
  + Base添加成功（Base SN在首页可见）
  三个条件同时满足 → 摄像机添加成功

依赖:
  - poco_helpers.py: Smart click, scroll, retry, page nav checks
  - config.py: Device SN, Camera SN, timeouts, identifiers
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
    DEVICE_SN, CAMERA_SN, PACKAGE_NAME,
    ADD_DEVICE_BTN_ID,
    SETTINGS_BTN_ID, DEVICE_INFO_BTN_ID,
    ELECTRICITY_ICON_ID, WIFI_NAME_ID,
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
    IDENTIFIER_ADD_TO_BASE, IDENTIFIER_SUB_DEVICE_MGMT,
    IDENTIFIER_UNBIND_DEVICE,
)


@allure.epic("Base设备管理")
@allure.feature("摄像机子设备添加与解绑")
@allure.story("基本操作流程")
@allure.title("摄像机添加与解绑 - 完整流程")
@allure.description(f"""
前置条件：
1. Base已配网并出现在首页
2. 摄像机已上电并靠近Base
3. Android手机连接与Base相同的网络
4. Base SN: {DEVICE_SN}，摄像机 SN: {CAMERA_SN}

测试流程：
- 预检查：清理已有设备（若存在）
- 步骤1-7：添加摄像机（添加Base→搜索摄像机SN→添加至Base→连接等待→返回首页）
- 步骤8-10：验证摄像机添加（Base子设备管理→检查摄像机SN）
- 步骤11-12：查看摄像机出流（进入摄像机→等待出流）
- 步骤13-14：验证摄像机绑定Base（设备信息→检查WiFi名称）
- 步骤15-19：删除摄像机并验证
""")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("P0", "冒烟测试")
@pytest.mark.p0
@pytest.mark.smoke
def test_camera_add_and_unbind(test_context):
    """
    完整摄像机添加→验证→删除→验证流程
    """
    poco = test_context["poco"]
    config = test_context["config"]
    base_sn = DEVICE_SN
    camera_sn = CAMERA_SN

    # ==================== PHASE 0: Pre-check ====================
    with allure.step("预检查：确保Base已存在，摄像机不存在"):
        _precheck_cleanup(poco, config, base_sn, camera_sn)
        check_current_activity()

    # ==================== PHASE 1: Add Camera (Steps 1-7) ====================
    with allure.step("====== PHASE 1: 添加摄像机 ======"):
        camera_added = _add_camera_flow(poco, config, base_sn, camera_sn)
        assert camera_added, "摄像机添加流程失败"

    # ==================== PHASE 2: Verify Camera in Sub-device Mgmt (Steps 8-10) ====================
    with allure.step("====== PHASE 2: 验证摄像机在Base子设备管理中 ======"):
        camera_in_sub = _verify_camera_in_sub_device(poco, config, base_sn, camera_sn)
        assert camera_in_sub, "子设备管理中未找到摄像机SN"

    # ==================== PHASE 3: Enter Camera & Wait for Streaming (Steps 11-12) ====================
    with allure.step("====== PHASE 3: 进入摄像机查看出流 ======"):
        streaming_ok = _verify_camera_streaming(poco, config, camera_sn)
        assert streaming_ok, "摄像机出流验证失败"

    # ==================== Camera Add Success: Combined Check ====================
    with allure.step("====== 判定：摄像机添加成功 ======"):
        # 摄像机添加成功标志 = 步骤8（Base设置页可进入） + 步骤12（出流正常） + Base添加成功
        step8_passed = camera_in_sub
        step12_passed = streaming_ok
        base_add_success = check_element_exists(poco, text=base_sn, timeout=5)

        camera_add_success = step8_passed and step12_passed and base_add_success
        print(f"[ADD-SUCCESS] Step8(子设备管理)={step8_passed}, Step12(出流)={step12_passed}, Base={base_add_success}")
        allure.attach(
            f"摄像机添加成功判定: Step8={step8_passed}, Step12={step12_passed}, Base={base_add_success}",
            name="AddSuccessCriteria", attachment_type=allure.attachment_type.TEXT)
        assert camera_add_success, (
            f"摄像机添加成功判定失败: Step8={step8_passed}, Step12={step12_passed}, Base={base_add_success}"
        )

    # ==================== PHASE 4: Verify Camera Bound to Base (Steps 13-14) ====================
    with allure.step("====== PHASE 4: 验证摄像机绑定到Base ======"):
        bind_ok = _verify_camera_bind_to_base(poco, config, base_sn)
        assert bind_ok, f"摄像机WiFi名称不匹配Base SN={base_sn}"

    # ==================== PHASE 5: Delete Camera (Steps 15-17) ====================
    with allure.step("====== PHASE 5: 删除摄像机 ======"):
        for del_cycle in range(config["max_delete_retries"]):
            with allure.step(f"删除循环 {del_cycle + 1}/{config['max_delete_retries']}"):
                delete_ok = _delete_camera_flow(poco, config, camera_sn, base_sn=base_sn)
                if delete_ok:
                    print(f"[DELETE] Camera '{camera_sn}' deleted on cycle {del_cycle + 1}")
                    break
                else:
                    print(f"[DELETE] Deletion cycle {del_cycle + 1} failed")
            if not delete_ok and del_cycle == config["max_delete_retries"] - 1:
                pytest.fail(f"摄像机删除失败：经过 {config['max_delete_retries']} 次循环后仍未成功删除（首页或子设备管理中仍存在）")

    # ==================== PHASE 6: Verify Camera Deleted (Steps 18-19) ====================
    with allure.step("====== PHASE 6: 验证摄像机已删除 ======"):
        camera_gone = _verify_camera_deleted(poco, config, base_sn, camera_sn)
        assert camera_gone, f"摄像机 {camera_sn} 删除后仍在子设备管理中"

    # ==================== Final: Verify Base add success ====================
    with allure.step("====== 最终判定：摄像机添加与删除成功 ======"):
        print(f"[RESULT] Camera '{camera_sn}' add → verify → delete → verify ALL PASSED")
        allure.attach(
            f"Camera {camera_sn} full flow passed at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            name="Result", attachment_type=allure.attachment_type.TEXT)


# ==================== Phase 0: Pre-check ====================
def _precheck_cleanup(poco, config, base_sn, camera_sn):
    """
    预检查：确保Base已添加到首页，且摄像机不存在。
    摄像机添加的前置条件是Base必须先存在于首页。
    - 如果摄像机已存在 → 先删除摄像机
    - 如果Base不存在 → 先添加Base
    - 如果Base已存在 → 直接进行摄像机添加流程
    """
    # Use longer timeout and retry for more reliable detection
    has_camera = False
    for attempt in range(3):
        has_camera = check_element_exists(poco, text=camera_sn, timeout=5)
        if has_camera:
            break
        print(f"[PRE-CHECK] Camera '{camera_sn}' not found (attempt {attempt+1}/3)")
        time.sleep(1)

    has_base = False
    for attempt in range(3):
        has_base = check_element_exists(poco, text=base_sn, timeout=5)
        if has_base:
            break
        print(f"[PRE-CHECK] Base '{base_sn}' not found by Poco (attempt {attempt+1}/3)")
        time.sleep(1)

    # If Poco can't detect Base, try ADB fallback
    if not has_base:
        import subprocess, re
        try:
            result = subprocess.run(
                ["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                capture_output=True, text=True, timeout=15
            )
            result = subprocess.run(
                ["adb", "shell", "cat", "/sdcard/ui.xml"],
                capture_output=True, text=True, timeout=5
            )
            if base_sn in result.stdout:
                has_base = True
                print(f"[PRE-CHECK] Base '{base_sn}' confirmed via ADB fallback")
        except Exception as e:
            print(f"[PRE-CHECK] ADB fallback error: {e}")

    # 1. Delete camera first if exists (camera depends on Base)
    if has_camera:
        print(f"[PRE-CHECK] Camera '{camera_sn}' exists on home, deleting first...")
        for cycle in range(config["max_delete_retries"]):
            if _delete_camera_flow(poco, config, camera_sn, base_sn=base_sn):
                print("[PRE-CHECK] Existing camera deleted successfully")
                break
        else:
            pytest.fail(f"预检查失败：摄像机 {camera_sn} 删除不成功")

    # 2. If Base not on home, add Base first
    if not has_base:
        print(f"[PRE-CHECK] Base '{base_sn}' not on home, adding Base first...")
        base_added = _add_base_only_flow(poco, config, base_sn)
        if not base_added:
            pytest.fail(f"预检查失败：Base {base_sn} 添加不成功")
        print("[PRE-CHECK] Base added successfully")
    else:
        print(f"[PRE-CHECK] Base '{base_sn}' already on home. Ready for camera test.")


# ==================== Phase 1: Add Camera Flow ====================
def _add_camera_flow(poco, config, base_sn, camera_sn):
    """
    添加摄像机流程（蓝牙配网，前提：Base已存在于首页）：
    步骤1：首页点击添加按钮→弹框选择「添加设备」
    步骤2：进入「选择设备类别」页面，在搜索到的设备列表中点击摄像机SN
    步骤3：点击「添加至Base/NVR」
    步骤4：等待连接完成
    步骤5：返回首页
    """
    failed_steps = []

    # ---- Step 0: Ensure we are on home page ----
    with allure.step("步骤0：确保回到首页"):
        print("[CAMERA-ADD] Ensuring home page...")
        check_current_activity()
        # If not on home, press BACK repeatedly until we see the add button
        for _ in range(5):
            if check_element_exists(poco, element_id=ADD_DEVICE_BTN_ID, timeout=3):
                print("[CAMERA-ADD] Already on home page (add button visible)")
                break
            print("[CAMERA-ADD] Not on home, pressing BACK...")
            go_back_to_home()
            time.sleep(2)
        else:
            # Final attempt: force close and relaunch
            print("[CAMERA-ADD] Still not on home, trying to relaunch app...")
            from airtest.core.api import start_app
            start_app("com.cloudedge.smarteye")
            time.sleep(5)
        check_current_activity()

    # ---- Step 1: Click add button on home → verify popup → click 添加设备 ----
    with allure.step("步骤1：首页点击添加按钮 → 验证弹框 → 点击「添加设备」"):
        # Wait for home page to fully load (Poco may need time after app launch)
        time.sleep(2)
        # Try clicking add button with retries
        add_btn_clicked = False
        for retry in range(3):
            if find_and_click_element(poco, ADD_DEVICE_BTN_ID, timeout=config["timeout"]):
                add_btn_clicked = True
                break
            print(f"[CAMERA-ADD] Add button not found (retry {retry+1}/3), waiting...")
            time.sleep(2)
        if not add_btn_clicked:
            failed_steps.append("步骤1-点击添加按钮")
            return False
        time.sleep(1)

        has_scan = check_element_exists(poco, text=IDENTIFIER_SCAN_QR, timeout=3)
        has_add = check_element_exists(poco, text=IDENTIFIER_ADD_POPUP, timeout=3)
        if not (has_scan and has_add):
            allure.attach(f"扫一扫={has_scan}, 添加设备={has_add}", name="弹框验证失败",
                         attachment_type=allure.attachment_type.TEXT)
            failed_steps.append("步骤1-弹框验证")
            return False
        print(f"[VERIFY] Popup confirmed: 扫一扫={has_scan}, 添加设备={has_add}")

        if not smart_click(poco, "text", IDENTIFIER_ADD_POPUP, timeout=5, description="添加设备"):
            failed_steps.append("步骤1-点击添加设备")
            return False
        if not verify_page_transition(poco, IDENTIFIER_ADD_POPUP, IDENTIFIER_DEVICE_CATEGORY, timeout=config["timeout"]):
            failed_steps.append("步骤1-页面跳转到选择设备类别")
            return False

    # ---- Step 2: In "选择设备类别" page, click Camera SN from search results ----
    with allure.step(f"步骤2：在「选择设备类别」页面搜索到的设备列表中点击摄像机SN={camera_sn}"):
        sn_found = _wait_and_select_sn(poco, camera_sn, config)
        if not sn_found:
            failed_steps.append(f"步骤2-搜索并点击摄像机SN={camera_sn}")
            return False

    # ---- Step 3: Click "添加至Base/NVR" after page transition ----
    with allure.step("步骤3：等待页面跳转，点击「添加至Base/NVR」"):
        time.sleep(2)
        if not smart_click(poco, "text", IDENTIFIER_ADD_TO_BASE, timeout=config["timeout"], description="添加至Base/NVR"):
            failed_steps.append("步骤3-添加至Base/NVR")
            return False

    # ---- Step 4: Wait for connection wizard to complete ----
    with allure.step("步骤4：等待设备连接向导完成（搜索设备→注册到云端→设备初始化→连接成功）"):
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
            if check_element_exists(poco, text=IDENTIFIER_DEVICE_INIT, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_DEVICE_INIT} in progress ({time.time()-conn_start:.0f}s)")
            elif check_element_exists(poco, text=IDENTIFIER_CLOUD_REGISTER, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_CLOUD_REGISTER} in progress ({time.time()-conn_start:.0f}s)")
            elif check_element_exists(poco, text=IDENTIFIER_CONNECTING, timeout=2):
                print(f"[CONNECT] {IDENTIFIER_CONNECTING} in progress ({time.time()-conn_start:.0f}s)")
            time.sleep(3)
        if not success_found:
            failed_steps.append("步骤4-连接超时")
            return False

    # ---- Step 5: Return to home page ----
    with allure.step("步骤5：连接成功后按物理返回键回到首页"):
        time.sleep(1)
        go_back_to_home()
        time.sleep(2)
        print(f"[CAMERA-ADD] Camera add flow completed at {time.strftime('%H:%M:%S')}")

    return True


# ==================== Shared: Navigate to Device Search Page ====================
def _navigate_to_device_search(poco, config):
    """
    导航到设备搜索页面（添加Base和添加摄像机共用）：
    首页→添加按钮→弹框验证→添加设备→选择设备类别→摄像机套装→BASE(网线)→下一步x2
    """
    failed_steps = []

    with allure.step("点击首页添加按钮"):
        if not find_and_click_element(poco, ADD_DEVICE_BTN_ID, timeout=config["timeout"]):
            failed_steps.append("点击添加按钮")
            return False
        time.sleep(1)

    with allure.step("验证弹框显示「扫一扫」和「添加设备」"):
        has_scan = check_element_exists(poco, text=IDENTIFIER_SCAN_QR, timeout=3)
        has_add = check_element_exists(poco, text=IDENTIFIER_ADD_POPUP, timeout=3)
        if not (has_scan and has_add):
            allure.attach(f"扫一扫={has_scan}, 添加设备={has_add}", name="弹框验证失败",
                         attachment_type=allure.attachment_type.TEXT)
            failed_steps.append("弹框验证")
            return False
        print(f"[VERIFY] Popup confirmed: 扫一扫={has_scan}, 添加设备={has_add}")

    with allure.step("点击「添加设备」→ 选择「摄像机套装」→ 点击「BASE(网线)」"):
        if not smart_click(poco, "text", IDENTIFIER_ADD_POPUP, timeout=5, description="添加设备"):
            failed_steps.append("点击添加设备")
            return False
        if not verify_page_transition(poco, IDENTIFIER_ADD_POPUP, IDENTIFIER_DEVICE_CATEGORY, timeout=config["timeout"]):
            failed_steps.append("页面跳转验证")
            return False
        time.sleep(0.5)
        if not click_with_scroll(poco, IDENTIFIER_CAMERA_KIT, max_scrolls=5):
            failed_steps.append("查找摄像机套装")
            return False
        time.sleep(1.5)
        if not click_with_scroll(poco, IDENTIFIER_BASE_WIRED, max_scrolls=5):
            failed_steps.append("点击BASE(网线)")
            return False
        time.sleep(0.5)

    with allure.step("点击两个「下一步」"):
        if not smart_click(poco, "text", IDENTIFIER_NEXT_BTN, timeout=config["next_btn_timeout"], description="下一步-1"):
            failed_steps.append("下一步1")
            return False
        if not smart_click(poco, "text", IDENTIFIER_NEXT_BTN, timeout=config["next_btn_timeout"], description="下一步-2"):
            failed_steps.append("下一步2")
            return False

    return True


# ==================== Helper: Add Base Only (for pre-check) ====================
def _add_base_only_flow(poco, config, base_sn):
    """
    仅添加Base设备（预检查使用）。
    流程：导航到搜索页→点击Base SN→等待连接→返回首页→验证Base在首页
    """
    # Navigate to search page
    if not _navigate_to_device_search(poco, config):
        return False

    # Click Base SN in search results
    if not _wait_and_select_sn(poco, base_sn, config):
        print(f"[PRE-CHECK] Failed to find Base '{base_sn}' in search")
        return False

    # Wait for connection
    conn_start = time.time()
    conn_timeout = config["connect_timeout"]
    success_found = False
    while time.time() - conn_start < conn_timeout:
        if check_element_exists(poco, text=IDENTIFIER_CONNECT_SUCCESS, timeout=2):
            print(f"[PRE-CHECK] Base connection success at {time.time()-conn_start:.0f}s")
            success_found = True
            break
        if check_element_exists(poco, text=IDENTIFIER_ADD_SUCCESS, timeout=2):
            print(f"[PRE-CHECK] Base add success at {time.time()-conn_start:.0f}s")
            success_found = True
            break
        time.sleep(3)
    if not success_found:
        print("[PRE-CHECK] Base connection timeout")
        return False

    # Return to home and verify
    time.sleep(1)
    go_back_to_home()
    time.sleep(2)
    base_on_home = check_element_exists(poco, text=base_sn, timeout=config["timeout"])
    if not base_on_home:
        print(f"[PRE-CHECK] Base '{base_sn}' not on home after add")
        return False
    print(f"[PRE-CHECK] Base '{base_sn}' confirmed on home")
    return True


# ==================== Phase 2: Verify Camera in Sub-device Mgmt ====================
def _verify_camera_in_sub_device(poco, config, base_sn, camera_sn):
    """
    步骤8-10：通过Base的通用设置→子设备管理，检查摄像机SN是否存在
    """
    failed_steps = []

    # ---- Step 8: Click Base SN on home ----
    with allure.step(f"步骤8：首页点击Base SN「{base_sn}」"):
        if not smart_click(poco, "text", base_sn, timeout=config["timeout"], description=f"Base SN={base_sn}"):
            failed_steps.append("步骤8-点击Base SN")
            return False

    # ---- Step 9: Verify settings page & click 通用设置 ----
    with allure.step("步骤9：等待进入Base设置页，点击「通用设置」"):
        time.sleep(3)
        page_ok = (
            check_element_exists(poco, text=IDENTIFIER_GENERAL_SETTINGS, timeout=config["timeout"]) or
            check_element_exists(poco, text=IDENTIFIER_SETTINGS, timeout=3) or
            check_element_exists(poco, text=IDENTIFIER_DELETE_BTN, timeout=3)
        )
        if not page_ok:
            failed_steps.append("步骤9-进入Base设置页")
            return False
        print("[VERIFY] Base settings page loaded")

        if not smart_click(poco, "text", IDENTIFIER_GENERAL_SETTINGS, timeout=config["timeout"], description="通用设置"):
            failed_steps.append("步骤9-点击通用设置")
            return False

    # ---- Step 10: Click 子设备管理 and check for camera SN ----
    with allure.step("步骤10：点击「子设备管理」，检查是否包含摄像机SN"):
        time.sleep(1)
        if not smart_click(poco, "text", IDENTIFIER_SUB_DEVICE_MGMT, timeout=config["timeout"], description="子设备管理"):
            failed_steps.append("步骤10-点击子设备管理")
            return False

        time.sleep(2)
        camera_found = check_element_exists(poco, text=camera_sn, timeout=config["timeout"])
        if not camera_found:
            allure.attach(f"Camera {camera_sn} not found in sub-device management",
                         name="子设备验证失败", attachment_type=allure.attachment_type.TEXT)
            failed_steps.append(f"步骤10-子设备管理中未找到{camera_sn}")
            return False
        print(f"[VERIFY] Camera '{camera_sn}' found in sub-device management")

    return True


# ==================== Phase 3: Verify Camera Streaming ====================
def _verify_camera_streaming(poco, config, camera_sn):
    """
    步骤11-12：返回首页→点击摄像机SN→忽略弹框→等待出流
    """
    failed_steps = []

    # ---- Step 11: Return to home and click camera SN ----
    with allure.step(f"步骤11：返回首页，点击摄像机SN「{camera_sn}」，忽略弹框"):
        go_back_to_home()
        time.sleep(2)

        if not smart_click(poco, "text", camera_sn, timeout=config["timeout"], description=f"Camera SN={camera_sn}"):
            failed_steps.append("步骤11-点击摄像机SN")
            return False

        # Dismiss any popups that may appear (取消/忽略/关闭)
        time.sleep(2)
        for dismiss_text in ["取消", "忽略", "关闭", "稍后", "暂不"]:
            try:
                if poco(text=dismiss_text).exists():
                    poco(text=dismiss_text).click()
                    print(f"[CAMERA] Dismissed popup: '{dismiss_text}'")
                    time.sleep(1)
            except Exception:
                pass

    # ---- Step 12: Wait for streaming indicator (iv_electricity) to appear ----
    with allure.step("步骤12：等待摄像机出流5秒（检测电量图标出现）"):
        stream_start = time.time()
        stream_timeout = config.get("stream_timeout", 60)
        electricity_found = False

        # Wait for the electricity icon to appear, then wait 5 more seconds
        while time.time() - stream_start < stream_timeout:
            if check_element_exists(poco, element_id=ELECTRICITY_ICON_ID, timeout=2):
                if not electricity_found:
                    print(f"[STREAM] Electricity icon appeared at {time.time()-stream_start:.0f}s, waiting 5s for stable stream...")
                    electricity_found = True
                    electricity_time = time.time()
                # Once found, wait 5 seconds to ensure stable streaming
                if electricity_found and time.time() - electricity_time >= 5:
                    print(f"[STREAM] Camera streaming stable for 5s confirmed")
                    break
            elif electricity_found:
                # Electricity icon disappeared, reset
                print(f"[STREAM] WARNING: Electricity icon disappeared, re-waiting...")
                electricity_found = False
            time.sleep(2)

        if not electricity_found:
            failed_steps.append("步骤12-摄像机出流超时")
            return False
        print(f"[STREAM] Camera streaming verified at {time.strftime('%H:%M:%S')}")

    return True


# ==================== Phase 4: Verify Camera Bound to Base ====================
def _verify_camera_bind_to_base(poco, config, base_sn):
    """
    步骤13-14：点击设置按钮→设备信息→检查WiFi名称是否为Base SN
    """
    failed_steps = []

    # ---- Step 13: Click settings button (top-right iv_submit) ----
    with allure.step("步骤13：点击右上角设置按钮"):
        time.sleep(1)
        if not find_and_click_element(poco, SETTINGS_BTN_ID, timeout=config["timeout"]):
            failed_steps.append("步骤13-点击设置按钮")
            return False
        time.sleep(2)

    # ---- Step 14: Click device info and check WiFi name ----
    with allure.step("步骤14：点击设备信息，检查WiFi名称为Base SN"):
        if not find_and_click_element(poco, DEVICE_INFO_BTN_ID, timeout=config["timeout"]):
            failed_steps.append("步骤14-点击设备信息")
            return False
        time.sleep(2)

        # Check tv_wifi_name2 text matches Base SN
        try:
            wifi_element = poco(name=WIFI_NAME_ID)
            wifi_element.wait_for_appearance(timeout=config["timeout"])
            wifi_text = wifi_element.get_text()
            print(f"[VERIFY] WiFi name text: '{wifi_text}', expected Base SN: '{base_sn}'")
            if base_sn in wifi_text or wifi_text == base_sn:
                print(f"[VERIFY] Camera bound to Base confirmed: WiFi={wifi_text}")
            else:
                allure.attach(f"WiFi text='{wifi_text}', expected='{base_sn}'",
                             name="WiFi名称不匹配", attachment_type=allure.attachment_type.TEXT)
                failed_steps.append(f"步骤14-WiFi名称不匹配: {wifi_text} != {base_sn}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to read WiFi name: {e}")
            failed_steps.append("步骤14-读取WiFi名称失败")
            return False

    return True


# ==================== Phase 5: Delete Camera Flow ====================
def _delete_camera_flow(poco, config, camera_sn, base_sn=None):
    """
    步骤15-17：从首页点击摄像机SN→进入摄像机页面→下滑找删除设备→解绑当前设备→返回首页
    →进入Base子设备管理验证摄像机SN已消失
    base_sn: 用于步骤17b验证子设备管理（可选，不传则跳过子设备管理验证）
    """
    failed_steps = []

    # ---- Step 15: From home, click camera SN → preview page → click gear settings → scroll to 删除设备 ----
    with allure.step("步骤15：首页点击摄像机SN→预览页→右上角齿轮设置→下滑找到「删除设备」"):
        # First ensure we're on home and click the camera SN
        if not check_element_exists(poco, text=camera_sn, timeout=3):
            # Not on home, go back to home first
            go_back_to_home()
            time.sleep(2)

        # Click camera SN on home to enter camera preview page
        if not smart_click(poco, "text", camera_sn, timeout=config["timeout"], description=f"Camera SN={camera_sn}"):
            failed_steps.append("步骤15-点击摄像机SN")
            return False
        time.sleep(3)

        # Dismiss any popups on preview page
        for dismiss_text in ["取消", "忽略", "关闭", "稍后", "暂不", "去体验"]:
            try:
                if poco(text=dismiss_text).exists():
                    poco(text=dismiss_text).click()
                    print(f"[DELETE] Dismissed popup: '{dismiss_text}'")
                    time.sleep(1)
            except Exception:
                pass

        # Click the gear settings button (iv_submit) in top-right corner of preview page
        print("[DELETE] Clicking gear settings button (iv_submit) in preview page...")
        if not find_and_click_element(poco, SETTINGS_BTN_ID, timeout=config["timeout"]):
            # Fallback: try clicking directly via Poco
            try:
                poco(name=SETTINGS_BTN_ID).click()
                time.sleep(2)
                print("[DELETE] Clicked settings button via name fallback")
            except Exception as e:
                print(f"[DELETE] Failed to click settings: {e}")
                failed_steps.append("步骤15-点击设置按钮")
                return False
        time.sleep(2)

        # Verify we're on settings page
        settings_page_confirmed = (
            check_element_exists(poco, text="设置", timeout=3) or
            check_element_exists(poco, text="通用设置", timeout=3) or
            check_element_exists(poco, text="设备分享", timeout=3)
        )
        if not settings_page_confirmed:
            print("[DELETE] WARNING: Settings page not confirmed, but continuing...")

        # Find and click 删除设备 (may need to scroll down - it's at the bottom)
        if not smart_click(poco, "text", IDENTIFIER_DELETE_BTN, timeout=3, description="删除设备"):
            # Scroll to find it: 删除设备 is at the bottom, need to drag content up
            if not click_with_scroll(poco, IDENTIFIER_DELETE_BTN, max_scrolls=8, scroll_direction="down"):
                failed_steps.append("步骤15-查找删除设备")
                return False

    # ---- Step 16: Click radio button next to "解绑当前设备" in popup ----
    with allure.step("步骤16：弹框中点击「解绑当前设备」旁边的圆点（文字不可点击，需点击兄弟圆点）"):
        time.sleep(1)
        unbind_clicked = False
        try:
            unbind_text = poco(text=IDENTIFIER_UNBIND_DEVICE)
            if unbind_text.exists():
                # "解绑当前设备"文字本身不可点击，找它同级的兄弟圆点（RadioButton/ImageView）
                parent = unbind_text.parent()
                if parent.exists():
                    # 遍历父容器下的子元素，找非文字的可点击元素（圆点）
                    for child in parent.children():
                        try:
                            child_type = child.attr("type") or ""
                            child_text = child.attr("text") or ""
                            # RadioButton 或 ImageView 类型的圆点，且不是文字元素
                            if child_text != IDENTIFIER_UNBIND_DEVICE and child_text != IDENTIFIER_DELETE_CONFIRM:
                                if "RadioButton" in child_type or "Image" in child_type or "CheckBox" in child_type:
                                    child.click()
                                    print(f"[DELETE] Clicked radio button (type={child_type}) next to 解绑当前设备")
                                    unbind_clicked = True
                                    break
                        except Exception:
                            pass
                    # 如果按类型没找到，尝试直接点 parent 下第一个非文字子元素
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
            # Fallback: try clicking the text directly (might work on some versions)
            if smart_click(poco, "text", IDENTIFIER_UNBIND_DEVICE, timeout=3, description="解绑当前设备(降级)"):
                unbind_clicked = True
        if not unbind_clicked:
            # Fallback: try "删除" or "确定"
            if not smart_click(poco, "text", IDENTIFIER_DELETE_CONFIRM, timeout=3, description="确认删除"):
                failed_steps.append("步骤16-解绑确认")
                return False

    # ---- Step 17: Confirm unbind, return to home, verify camera gone from home & sub-device mgmt ----
    with allure.step("步骤17：点击确定，等待页面返回首页，验证摄像机从首页和子设备管理消失"):
        time.sleep(1)
        # Click "确定" if present
        try:
            if poco(text="确定").exists():
                poco(text="确定").click()
                print("[DELETE] Clicked 确定 to confirm unbind")
        except Exception:
            pass
        time.sleep(3)  # Wait for auto-navigation back to home

        # ---- 17a: Verify camera is gone from home ----
        time.sleep(1)
        camera_on_home = check_element_exists(poco, text=camera_sn, timeout=3)
        if camera_on_home:
            print(f"[DELETE] Camera '{camera_sn}' still on home after unbind")
            # Try pull-to-refresh
            for _ in range(config["refresh_count_on_delete"]):
                if not check_element_exists(poco, text=camera_sn, timeout=2):
                    print(f"[DELETE] Camera '{camera_sn}' gone from home after refresh")
                    break
                pull_to_refresh(poco, times=1)
            else:
                failed_steps.append("步骤17a-首页摄像机仍存在")
                return False
        else:
            print(f"[DELETE] Camera '{camera_sn}' removed from home")

        # ---- 17b: Enter Base sub-device mgmt and verify camera SN is gone ----
        if base_sn:
            print(f"[DELETE] Step 17b: Entering Base sub-device management to verify camera SN is gone...")
            if not smart_click(poco, "text", base_sn, timeout=config["timeout"], description=f"Base SN={base_sn}"):
                failed_steps.append("步骤17b-点击Base SN")
                return False
            time.sleep(3)

            if not smart_click(poco, "text", IDENTIFIER_GENERAL_SETTINGS, timeout=config["timeout"], description="通用设置"):
                failed_steps.append("步骤17b-点击通用设置")
                return False
            time.sleep(1)

            if not smart_click(poco, "text", IDENTIFIER_SUB_DEVICE_MGMT, timeout=config["timeout"], description="子设备管理"):
                failed_steps.append("步骤17b-点击子设备管理")
                return False
            time.sleep(2)

            camera_in_sub = check_element_exists(poco, text=camera_sn, timeout=config["timeout"])
            if camera_in_sub:
                allure.attach(f"Camera {camera_sn} still in sub-device management after delete",
                             name="删除后子设备管理仍有摄像机", attachment_type=allure.attachment_type.TEXT)
                failed_steps.append(f"步骤17b-摄像机{camera_sn}仍存在于子设备管理")
                return False
            print(f"[DELETE] Camera '{camera_sn}' confirmed gone from sub-device management")

            # Return to home
            go_back_to_home()
            time.sleep(2)
        else:
            print(f"[DELETE] base_sn not provided, skipping sub-device mgmt verification")

        print(f"[DELETE] Camera '{camera_sn}' delete verified: home=gone, sub-device mgmt={('gone' if base_sn else 'skipped')}")
        return True


# ==================== Phase 6: Verify Camera Deleted ====================
def _verify_camera_deleted(poco, config, base_sn, camera_sn):
    """
    步骤18-19：进入Base→通用设置→子设备管理→检查摄像机SN是否已不存在
    """
    failed_steps = []

    with allure.step(f"步骤18：点击Base SN「{base_sn}」→ 通用设置 → 子设备管理"):
        if not smart_click(poco, "text", base_sn, timeout=config["timeout"], description=f"Base SN={base_sn}"):
            failed_steps.append("步骤18-点击Base SN")
            return False
        time.sleep(3)

        if not smart_click(poco, "text", IDENTIFIER_GENERAL_SETTINGS, timeout=config["timeout"], description="通用设置"):
            failed_steps.append("步骤18-点击通用设置")
            return False
        time.sleep(1)

        if not smart_click(poco, "text", IDENTIFIER_SUB_DEVICE_MGMT, timeout=config["timeout"], description="子设备管理"):
            failed_steps.append("步骤18-点击子设备管理")
            return False
        time.sleep(2)

    with allure.step(f"步骤19：验证子设备管理中不包含摄像机SN「{camera_sn}」"):
        camera_still_exists = check_element_exists(poco, text=camera_sn, timeout=config["timeout"])
        if camera_still_exists:
            allure.attach(f"Camera {camera_sn} still in sub-device management",
                         name="摄像机删除验证失败", attachment_type=allure.attachment_type.TEXT)
            failed_steps.append(f"步骤19-摄像机{camera_sn}仍存在于子设备管理")
            return False
        print(f"[VERIFY] Camera '{camera_sn}' successfully removed from sub-device management")

    return True


# ==================== Reusable: Base Delete Flow (same as test_base_add_unbind) ====================
def _delete_base_flow(poco, config, base_sn):
    """删除Base设备（复用Base测试中的删除流程）"""
    # ---- Click Base SN on home ----
    if not smart_click(poco, "text", base_sn, timeout=config["timeout"], description=f"Base SN={base_sn}"):
        return False

    # ---- Wait for settings page ----
    time.sleep(3)
    page_ok = (
        check_element_exists(poco, text=IDENTIFIER_DELETE_BTN, timeout=config["timeout"]) or
        check_element_exists(poco, text=IDENTIFIER_SETTINGS, timeout=3) or
        check_element_exists(poco, text=IDENTIFIER_GENERAL_SETTINGS, timeout=3) or
        check_element_exists(poco, text=IDENTIFIER_DEVICE_SHARE, timeout=3)
    )
    if not page_ok:
        return False

    # ---- Click delete ----
    if not smart_click(poco, "text", IDENTIFIER_DELETE_BTN, timeout=config["timeout"], description="删除设备"):
        return False

    # ---- Confirm delete ----
    if not smart_click(poco, "text", IDENTIFIER_DELETE_CONFIRM, timeout=5, description="确认删除"):
        return False

    # ---- Verify removed ----
    time.sleep(3)
    for _ in range(config["refresh_count_on_delete"]):
        time.sleep(2)
        if not check_element_exists(poco, text=base_sn, timeout=3):
            print(f"[DELETE] Base '{base_sn}' removed from home")
            return True
        pull_to_refresh(poco, times=1)

    return False


# ==================== Helper: Wait for SN in search ====================
def _wait_and_select_sn(poco, device_sn, config):
    """Wait for target device SN to appear in search results and click it."""
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
                if attempt < config["max_search_retries"] - 1:
                    try:
                        poco(text=IDENTIFIER_CANCEL_BTN).click()
                        time.sleep(2)
                    except Exception:
                        print("[SEARCH] Could not click cancel button")

    print(f"[SEARCH] FAILED: Could not find '{device_sn}' after {config['max_search_retries']} attempts")
    return False
