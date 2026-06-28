"""
Test Configuration
Centralized config for Base device add/unbind automation tests.
"""
import os

# ==================== Device Info ====================
DEVICE_ID = "TC55LJMR59W8ZPRK"          # ADB device serial
DEVICE_MODEL = "Xiaomi 21091116AC"       # Device model name

# ==================== App Info ====================
PACKAGE_NAME = "com.cloudedge.smarteye"
HOME_ACTIVITY = "com.ppstrong.weeye.view.activity.MainActivity"

# ==================== Test Target ====================
DEVICE_SN = "129653415"                  # Base device SN to search and connect
CAMERA_SN = "126042320"                   # Camera (子设备) SN

# ==================== Element IDs ====================
ADD_DEVICE_BTN_ID = "com.cloudedge.smarteye:id/ivAddDevice"
SETTINGS_BTN_ID = "com.cloudedge.smarteye:id/iv_submit"              # Settings button (top-right)
DEVICE_INFO_BTN_ID = "com.cloudedge.smarteye:id/iv_right_device_info" # Device info button
ELECTRICITY_ICON_ID = "com.cloudedge.smarteye:id/iv_electricity"      # Streaming indicator (battery icon)
WIFI_NAME_ID = "com.cloudedge.smarteye:id/tv_wifi_name2"             # WiFi/Base SN display

# ==================== Page Identifiers (for transition verification) ====================
# -- Add device flow --
IDENTIFIER_SCAN_QR = "扫一扫"            # Scan QR code option on add popup
IDENTIFIER_ADD_POPUP = "添加设备"        # Add device option on popup
IDENTIFIER_DEVICE_CATEGORY = "选择设备类别"  # Page title after clicking 添加设备
IDENTIFIER_CAMERA_KIT = "摄像机套装"     # Camera kit option
IDENTIFIER_BASE_WIRED = "BASE"           # Base wired option (text is split: "BASE" + "(网线)" are separate elements)
IDENTIFIER_NEXT_BTN = "下一步"           # Next button in wizard
IDENTIFIER_CANCEL_BTN = "取消"           # Cancel button in search
# -- Connection wizard steps --
IDENTIFIER_CONNECTING = "搜索设备"       # Step 1: Searching for device
IDENTIFIER_CLOUD_REGISTER = "注册到云端"  # Step 2: Registering to cloud
IDENTIFIER_DEVICE_INIT = "设备初始化"     # Step 3: Device initialization
IDENTIFIER_CONNECT_SUCCESS = "连接成功"   # Step 4: Connection success
IDENTIFIER_ADD_SUCCESS = "添加设备成功"   # Alternative success text
# -- Delete device flow --
IDENTIFIER_SETTINGS = "设置"             # Settings page title
IDENTIFIER_GENERAL_SETTINGS = "通用设置"  # General settings option
IDENTIFIER_DEVICE_SHARE = "设备分享"      # Device share option
IDENTIFIER_DELETE_BTN = "删除设备"       # Delete button in settings
IDENTIFIER_DELETE_CONFIRM = "删除"       # Confirm delete in popup
# -- Camera specific --
IDENTIFIER_ADD_TO_BASE = "添加至Base/NVR"   # Add camera to Base/NVR
IDENTIFIER_SUB_DEVICE_MGMT = "子设备管理"    # Sub-device management page
IDENTIFIER_UNBIND_DEVICE = "解绑当前设备"    # Unbind current device popup

# ==================== Timeouts (seconds) ====================
TIMEOUT_CLICK = 15                       # Default click timeout
TIMEOUT_PAGE_TRANSITION = 15             # Page transition wait
TIMEOUT_NEXT_BTN = 60                    # Wait for 下一步 button
TIMEOUT_SEARCH_DEVICE = 90               # Wait for device SN in search
TIMEOUT_CONNECT = 120                    # Wait for device to connect
TIMEOUT_DELETE = 15                      # Delete operation timeout
TIMEOUT_APP_LAUNCH = 10                  # App launch wait
TIMEOUT_STREAM = 60                      # Wait for camera streaming (iv_electricity)
TIMEOUT_SUB_DEVICE = 30                  # Wait for sub-device management page

# ==================== Retry Config ====================
MAX_SEARCH_RETRIES = 3                   # Max search retries for device SN
MAX_DELETE_RETRIES = 3                   # Max delete retry cycles
REFRESH_COUNT_ON_DELETE = 3              # Pull-to-refresh times after delete
RETRY_DELAY = 2                          # Delay between retries (seconds)

# ==================== Project Paths ====================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ALLURE_RESULTS_DIR = os.path.join(PROJECT_ROOT, "allure-results")
TEST_CASES_DIR = os.path.join(PROJECT_ROOT, "test_cases")

# Ensure output directories exist
os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
os.makedirs(TEST_CASES_DIR, exist_ok=True)
