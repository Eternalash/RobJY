# AGENTS.md

## Cursor Cloud specific instructions

RobJY 是一个 **Python 3.11+ CLI 工具**（无服务端/前端进程），用 Playwright 驱动 Chromium
自动化上海九院齐脉 H5（`h5.shqmxx.com`）门诊预约。开发命令详见 `README.md`；下面只记录
非显而易见、易踩坑的点。

### 环境与运行

- 依赖装在项目根的 `.venv`（更新脚本自动维护）。运行前先 `source .venv/bin/activate`，
  或直接用 `.venv/bin/python`。系统包 `python3.12-venv` 已在环境快照中安装，更新脚本不再处理。
- Playwright 浏览器只装了 `chromium`（headless-shell）。
- 测试：`python -m pytest`（17 个纯单元测试，使用 fake page，不联网、不起浏览器，秒级完成）。
- 本仓库**未配置 lint 工具**（无 ruff/flake8/black），无 lint 步骤。

### CLI 参数顺序（重要坑）

`-c/--config` 与 `-v/--verbose` 是**顶层参数，必须放在子命令之前**，否则 argparse 报
`unrecognized arguments`。README 里 `... import-cookie ... -c config/local.yaml` 的顺序会失败。
正确写法：

```bash
python scripts/grab.py -c config/local.yaml import-cookie --cookie-file /tmp/jy.cookie
python scripts/grab.py -c config/local.yaml -v once --stop-before-captcha --headless
```

### 云环境里的可运行范围

- 云 VM 无显示器，只能 headless。`config/local.yaml` 里请设 `session.headless: true`
  （`config/local.yaml`、`.data/` 均被 gitignore）。
- `login` 子命令需要**有头浏览器 + 人工微信授权**，云环境无法完成真实登录。
- 离线可完整跑通的核心路径：`import-cookie`（Cookie 文本 → `storage_state.json`）
  以及 `once --headless`（启动 Chromium、注入会话、导航真实入口、执行预约状态机）。
  用非真实 cookie 时，`once` 会正确地在登录态探测处判定"未登录"并在 `.data/artifacts/`
  截图存档——这是预期结果，可作为浏览器全链路可用的证明。真实约号需要真实微信会话。

### 已知非阻塞瑕疵

- `BrowserSession.close()` 用 `Playwright.close()`（应为 `.stop()`）。异常已被 `except`
  吞掉，仅在 `-v`(DEBUG) 下会打印一段 teardown traceback，不影响命令退出码与结果。
