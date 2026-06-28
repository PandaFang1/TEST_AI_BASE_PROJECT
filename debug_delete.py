"""
调试脚本：仅测试删除单个摄像机（解绑当前设备）
前置条件：首页 Base 和摄像机均已存在
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airtest.core.api import connect_device, start_app, sleep, keyevent
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

connect_device('Android:///TC55LJMR59W8ZPRK')

# Monkey-patches
from poco.drivers.android.utils import installation
_orig_uninstall = installation.uninstall
def _safe_uninstall(adb_client, package_name):
    try:
        _orig_uninstall(adb_client, package_name)
    except Exception as e:
        import warnings
        warnings.warn(f"Ignored uninstall error for {package_name}: {e}")
installation.uninstall = _safe_uninstall

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

from config import CAMERA_SN, SETTINGS_BTN_ID, IDENTIFIER_DELETE_BTN, IDENTIFIER_UNBIND_DEVICE, IDENTIFIER_DELETE_CONFIRM
from poco_helpers import smart_click, click_with_scroll, find_and_click_element, check_element_exists

print("=" * 60)
print("初始化 Poco...")
print("=" * 60)
start_app("com.cloudedge.smarteye")
sleep(5)
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)
camera_sn = CAMERA_SN

# Step 1: 确认首页状态
print("\n[STEP 1] 确认首页摄像机存在...")
sleep(1)
if not check_element_exists(poco, text=camera_sn, timeout=5):
    print(f"[ERROR] 摄像机 {camera_sn} 不在首页！")
    sys.exit(1)
print(f"[OK] 摄像机 {camera_sn} 在首页")

# Step 2: 点击摄像机进入预览页
print("\n[STEP 2] 点击摄像机进入预览页...")
if not smart_click(poco, "text", camera_sn, timeout=15):
    print("[ERROR] 点击摄像机失败")
    sys.exit(1)
sleep(3)

# 关闭弹框
for dismiss_text in ["取消", "忽略", "关闭", "稍后", "暂不", "去体验"]:
    try:
        if poco(text=dismiss_text).exists():
            poco(text=dismiss_text).click()
            print(f"[INFO] 关闭弹框: '{dismiss_text}'")
            sleep(1)
    except Exception:
        pass

# Step 3: 点击设置按钮
print("\n[STEP 3] 点击设置按钮...")
if not find_and_click_element(poco, SETTINGS_BTN_ID, timeout=15):
    try:
        poco(name=SETTINGS_BTN_ID).click()
        sleep(2)
        print("[INFO] 通过 name fallback 点击设置")
    except Exception as e:
        print(f"[ERROR] 点击设置失败: {e}")
        sys.exit(1)
sleep(2)

# 确认设置页
settings_ok = (
    check_element_exists(poco, text="设置", timeout=3) or
    check_element_exists(poco, text="通用设置", timeout=3) or
    check_element_exists(poco, text="设备分享", timeout=3)
)
print(f"[INFO] 设置页确认: {settings_ok}")

# Step 4: 找删除设备（在底部，需滚动）
print("\n[STEP 4] 查找删除设备...")
if not smart_click(poco, "text", IDENTIFIER_DELETE_BTN, timeout=3):
    print("[INFO] 直接点击失败，滚动查找...")
    if not click_with_scroll(poco, IDENTIFIER_DELETE_BTN, max_scrolls=8, scroll_direction="down"):
        print("[ERROR] 找不到删除设备")
        sys.exit(1)
print("[OK] 已点击删除设备")

# Step 5: 弹框出现，检查元素
print("\n[STEP 5] 检查弹框元素结构...")
sleep(2)

# 检查弹框中都有什么文字
print("[DUMP] 弹框内可见文字:")
all_texts = set()
try:
    root = poco(name="com.cloudedge.smarteye:id/parentPanel")
    if not root.exists():
        root = poco(name="android:id/parentPanel")
    if root.exists():
        for child in root.offspring():
            try:
                t = child.attr("text")
                if t:
                    all_texts.add(t)
            except:
                pass
    else:
        # 遍历顶层所有元素
        for elem in poco().offspring():
            try:
                t = elem.attr("text")
                if t and t.strip():
                    all_texts.add(t.strip())
            except:
                pass
except Exception as e:
    print(f"[ERROR] 遍历弹框失败: {e}")

for t in sorted(all_texts):
    print(f"  - '{t}'")

# Step 6: 点击解绑当前设备旁边的圆点
print(f"\n[STEP 6] 点击「{IDENTIFIER_UNBIND_DEVICE}」旁边的圆点...")
unbind_clicked = False

try:
    unbind_text = poco(text=IDENTIFIER_UNBIND_DEVICE)
    if unbind_text.exists():
        elem_type = unbind_text.attr("type")
        clickable = unbind_text.attr("clickable")
        print(f"[INFO] 解绑当前设备: type={elem_type}, clickable={clickable}")

        parent = unbind_text.parent()
        if parent.exists():
            parent_type = parent.attr("type")
            print(f"[INFO] 父容器: type={parent_type}, children count={len(list(parent.children()))}")
            for child in parent.children():
                ct = child.attr("type") or ""
                ctext = child.attr("text") or ""
                cclickable = child.attr("clickable")
                print(f"  child: type={ct}, text='{ctext}', clickable={cclickable}")

            # 找 RadioButton/ImageView/CheckBox
            for child in parent.children():
                try:
                    ct = child.attr("type") or ""
                    ctext = child.attr("text") or ""
                    if ctext != IDENTIFIER_UNBIND_DEVICE:
                        if "RadioButton" in ct or "Image" in ct or "CheckBox" in ct:
                            child.click()
                            print(f"[OK] Clicked radio button: type={ct}")
                            unbind_clicked = True
                            break
                except:
                    pass
            # 降级：点空文字子元素
            if not unbind_clicked:
                for child in parent.children():
                    try:
                        ctext = child.attr("text") or ""
                        if not ctext:
                            child.click()
                            print(f"[OK] Clicked empty-text sibling")
                            unbind_clicked = True
                            break
                    except:
                        pass
except Exception as e:
    print(f"[ERROR] 查找圆点失败: {e}")

if not unbind_clicked:
    print("[WARN] 未找到圆点，尝试直接点击文字...")
    if smart_click(poco, "text", IDENTIFIER_UNBIND_DEVICE, timeout=3):
        unbind_clicked = True
if not unbind_clicked:
    print("[ERROR] 无法点击解绑当前设备")
    sys.exit(1)

# Step 7: 确认
print("\n[STEP 7] 点击确定...")
sleep(1)
try:
    if poco(text="确定").exists():
        poco(text="确定").click()
        print("[OK] 已点击确定")
except:
    pass

sleep(4)

# Step 8: 验证结果
print("\n[STEP 8] 验证删除结果...")
camera_gone = not check_element_exists(poco, text=camera_sn, timeout=3)
print(f"[RESULT] 摄像机已从首页移除: {camera_gone}")

if not camera_gone:
    for i in range(3):
        from poco_helpers import pull_to_refresh
        pull_to_refresh(poco, times=1)
        if not check_element_exists(poco, text=camera_sn, timeout=2):
            camera_gone = True
            break

# 检查Base是否还在
from config import DEVICE_SN
base_still = check_element_exists(poco, text=DEVICE_SN, timeout=5)
print(f"[RESULT] Base仍在首页: {base_still}")

print("\n" + "=" * 60)
if camera_gone and base_still:
    print("✓ 成功！摄像机已单独删除，Base仍在首页")
else:
    print(f"✗ 结果: 摄像机已删除={camera_gone}, Base仍在={base_still}")
print("=" * 60)
