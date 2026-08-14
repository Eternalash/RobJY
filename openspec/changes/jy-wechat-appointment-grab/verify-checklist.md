# 场景自测 Checklist（对照 specs）

日期：2026-07-29  
环境：单元测试 + 代码静态对照（真实微信 H5 需本机有头登录后验证）

## h5-session-auth

- [x] 导出/复用 storage_state 路径可配置（`session.state_path`）— 代码：`BrowserSession.login_interactive` / `open_with_state`
- [x] 登录态探测多信号 / OAuth 页判定失败 — 单测：`tests/test_session_auth_detect.py`
- [x] 入口 URL 来自配置 — `config/example.yaml` + `load_config`

## outpatient-booking-flow

- [x] 状态机覆盖 AuthReady→…→Submitted/Failed — `BookingFlow`
- [x] 须知「是」→「我知道了」— `ShqmxxAdapter.accept_notice`
- [x] 日期预约 / 时段确认 / 就诊人 / 验证码+confirm_submit — adapter + flow
- [x] 逐步截图落盘 — `BookingFlow._shot`
- [ ] 真实页面端到端（需本机微信授权）— 运行：`python scripts/grab.py once --stop-before-captcha`

## selection-priority

- [x] 南部优先于高科 — `tests/test_priority_policy.py`
- [x] 主任优先于副主任 — 同上
- [x] 科室匹配 exact/contains + 未找到报错 — 同上
- [x] tie-break 最早日期/时段 — 同上

## release-scheduler

- [x] Asia/Shanghai 07:30 解析 — `tests/test_config_and_scheduler_time.py`
- [x] CLI `once` / `schedule` — `robjy.cli`
- [x] 轮询间隔与 max_attempts / 窗口结束汇总 — `ReleaseScheduler.run_scheduled`
- [ ] 真实放号窗口演练 — 需工作日 07:30 人工观察

## 结论

策略、配置、会话探测与 CLI 已由自动化测试覆盖；齐脉真实 DOM 适配需在授权环境用 `--stop-before-captcha` 回归。
