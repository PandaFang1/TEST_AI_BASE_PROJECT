---
name: Base设备添加解绑自动化脚本
overview: 基于用户提供的20步操作流程、已连接的Android手机（TC55LJMR59W8ZPRK）、SmartEye App（com.cloudedge.smarteye），结合poco-framework和pytest-allure两个skill，生成一个完整的Poco自动化测试脚本，包含设备添加、验证、删除、重试等完整流程。
todos:
  - id: create-project-structure
    content: 创建项目目录结构（test_cases目录、allure-results目录）
    status: completed
  - id: copy-poco-helpers
    content: 使用[skill:poco-framework]从skill复制poco_helpers.py到项目，并增加check_current_activity和verify_page_transition两个页面导航函数
    status: completed
    dependencies:
      - create-project-structure
  - id: create-config
    content: 创建config.py，配置DEVICE_SN、PACKAGE_NAME、各阶段超时参数和重试次数
    status: completed
    dependencies:
      - create-project-structure
  - id: create-conftest
    content: 使用[skill:pytest-allure]基于conftest_template.py创建conftest.py，包含global_config/app_foreground/poco_instance/test_context fixtures及失败截图hook
    status: completed
    dependencies:
      - create-project-structure
  - id: create-pytest-ini
    content: 使用[skill:pytest-allure]创建pytest.ini，配置alluredir、strict-markers和smoke/p0/p1/p2标记
    status: completed
    dependencies:
      - create-project-structure
  - id: create-test-case
    content: 使用[skill:poco-framework]和[skill:pytest-allure]生成test_base_add_unbind.py，实现完整的20步添加与解绑流程，包含Allure step注解、页面导航三检查、搜索重试、删除重试、预检查清理等全部逻辑
    status: completed
    dependencies:
      - copy-poco-helpers
      - create-config
      - create-conftest
---

## 用户需求

根据之前描述的20步Base设备添加与解绑操作流程，结合已连接的手机（TC55LJMR59W8ZPRK）、运行的App（com.cloudedge.smarteye）以及poco-framework和pytest-allure两个Skill，生成可直接运行的自动化测试脚本。

## 20步操作流程

1. 首页点击id为`com.cloudedge.smarteye:id/ivAddDevice`
2. 弹框显示"扫一扫"和"添加设备"
3. 点击"添加设备"
4. 查找"摄像机套装"，找不到则下滑寻找
5. 点击"摄像机套装"，出现"BASE(网线)"
6. 点击"BASE(网线)"
7. 等待"下一步"按钮可点击后点击
8. 等待"下一步"按钮可点击后点击
9. 等待设备SN号出现后点击；超时则记录时间→取消→重试，最多3次，3次失败则停止脚本
10. 等待跳转到等待连接界面
11. 连接成功后跳转连接成功界面
12. 物理按键返回首页，检查SN设备是否出现
13. 步骤11和12均成功则配网成功
14. 首页点击设备SN号
15. 进入设备设置页面
16. 点击删除设备按钮
17. 弹框点击删除确认
18. 返回首页，检查SN是否还存在，存在则下拉刷新3次
19. 删除失败提示第几次失败，重复步骤14-18共三遍
20. 添加前检查设备是否存在，存在则先删除，删除不成功则提示删除失败

## 环境信息

- 设备ID：TC55LJMR59W8ZPRK（Xiaomi 21091116AC）
- App包名：com.cloudedge.smarteye
- 首页Activity：com.ppstrong.weeye.view.activity.MainActivity

## Skill资源

- poco-framework：元素定位优先级、页面导航三检查、辅助函数
- pytest-allure：conftest模板、Allure装饰器/step/attachment、失败截图hook

## 技术栈

- **测试框架**：pytest + allure-pytest（报告）
- **UI自动化**：Airtest + Poco（AndroidUiautomationPoco后端）
- **语言**：Python 3
- **设备连接**：ADB over USB

## 实现方案

### 整体策略

将poco-framework skill的辅助函数（poco_helpers.py）与pytest-allure skill的conftest模板融合，生成一个完整的、可直接运行的测试项目。核心思路：

1. **复用现有Skill资产**：poco_helpers.py直接复制到项目，conftest.py从pytest-allure模板派生
2. **按20步流程生成测试用例**：添加流程（步骤1-13）和删除流程（步骤14-19）作为两个Allure step分组的pytest测试函数
3. **预检查逻辑**：步骤20在测试函数开头实现
4. **页面导航三检查**：融入每个页面跳转点

### 关键优化点

- **步骤4"摄像机套装"**：使用click_with_scroll而非硬编码点击，覆盖元素不在首屏场景
- **步骤9搜索重试**：wait_and_select_device_sn已实现3次重试+取消返回+搜索时间记录
- **步骤18-19删除重试**：delete_device_flow已实现max_retries=3，verify_device_removed实现3次下拉刷新检查
- **步骤20预检查**：pre_check_cleanup调用delete_device_flow做清理
- **Activity归属检查**：融入smart_click失败后的check_current_activity调用
- **页面识别点**：每个跳转后等待目标页面独有元素

### 性能考虑

- Poco实例初始化耗时约2-3秒，使用function级fixture确保每次测试独立
- screenshot_each_action=False避免每步截图拖慢速度
- sleep使用适中值（0.5-2秒），兼顾稳定性和速度

## 项目结构

```
/Users/fangxiaoc/Desktop/test_ai_base_project/
├── conftest.py              # [NEW] pytest fixtures + Allure配置
├── pytest.ini               # [NEW] pytest配置
├── poco_helpers.py          # [NEW] 从poco-framework skill复制的辅助函数
├── config.py                # [NEW] 设备配置（SN、包名、超时等）
├── test_cases/
│   └── test_base_add_unbind.py  # [NEW] 主测试用例（添加+删除完整流程）
└── allure-results/          # [NEW] Allure结果输出目录（运行时生成）
```

## 实现细节

### conftest.py

- 从pytest-allure skill的conftest_template.py派生
- global_config fixture包含device_sn、package_name等配置
- app_foreground fixture确保app前台运行
- poco_instance fixture提供Poco实例
- test_context fixture聚合所有依赖
- pytest_runtest_makereport hook实现失败自动截图

### config.py

- DEVICE_SN：待填写的设备SN号
- PACKAGE_NAME：com.cloudedge.smarteye
- 各步骤超时配置

### poco_helpers.py

- 直接从poco-framework skill复制，10个函数全部可用
- 额外增加check_current_activity和verify_page_transition两个函数

### test_base_add_unbind.py

- 两个测试函数：
- test_base_device_add_unbind：完整添加→验证→删除→验证流程（步骤1-20）
- 可选：test_pre_check_cleanup单独测试预检查逻辑
- 每个函数带完整Allure装饰器（epic/feature/story/title/description/severity/tag）
- 每个逻辑步骤用with allure.step包裹
- 失败时自动截图并附加到Allure报告

## Agent Extensions

### Skill

- **poco-framework**
- 目的：提供Poco元素定位优先级规范、页面导航三检查模式、smart_click/click_with_scroll/retry_operation等辅助函数
- 预期结果：生成的测试脚本遵循定位优先级（基本选择器>相对选择器>空间顺序>正则），每个页面跳转后执行识别点检查、Activity归属检查和跳转验证

- **pytest-allure**
- 目的：提供conftest模板（fixtures/失败截图hook）、Allure装饰器规范（epic/feature/story/step/attachment）、pytest.ini配置模板
- 预期结果：生成的conftest.py包含完整的fixture链和失败截图hook，测试用例带完整Allure注解，pytest.ini正确配置摄像机套装"找到了（在滑动1次后找到并点击）