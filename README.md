# RobJY

上海第九人民医院微信公众号（齐脉 H5：`h5.shqmxx.com`）门诊预约辅助工具。

**仅限本人合法就医用途。** 请遵守医院与微信服务条款；勿用于倒号、倒卖或批量占号。默认开启最终提交确认（`confirm_submit: true`），验证码需人工输入。

## 功能

1. 半自动模拟登录：有头浏览器完成微信授权，导出 `storage_state` 复用
2. 门诊预约流程自动化（须知 → 院区/科室 → 医师日期 → 时段 → 就诊人 → 验证码）
3. 院区优先级：南部院区 → 高科园区（可配置）
4. 医师职称优先级：主任医师 → 副主任医师（可配置）
5. 每日 07:30（`Asia/Shanghai`）放号窗口热身 + 轮询

## 环境

- Python 3.11+
- Playwright（Chromium）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp config/example.yaml config/local.yaml
# 编辑 config/local.yaml：科室、就诊人等
```

## 用法

```bash
# 1) 首次登录：弹出浏览器，在微信授权完成后自动保存会话
python scripts/grab.py login -c config/local.yaml

# 2) 立即跑一遍流程（调试；建议先加 --stop-before-captcha）
python scripts/grab.py once -c config/local.yaml --stop-before-captcha

# 3) 按 07:30 调度抢号
python scripts/grab.py schedule -c config/local.yaml
```

等价入口（安装包后）：`robjy-grab login|once|schedule -c config/local.yaml`。

## 配置要点

见 `config/example.yaml`：

| 字段 | 含义 |
|------|------|
| `site.entry_url` | 齐脉 H5 入口 |
| `session.state_path` | Playwright 会话文件 |
| `booking.department` | 目标科室 |
| `booking.campus_priority` | 院区优先级 |
| `booking.title_priority` | 职称优先级 |
| `booking.patient_name` | 就诊人 |
| `booking.confirm_submit` | 最终提交前终端确认 |
| `scheduler.release_time` | 放号时刻，默认 `07:30:00` |

`config/local.yaml`、`.data/`（会话、截图、验证码）已加入 `.gitignore`，请勿提交隐私数据。

## 项目结构

```
src/robjy/
  session/     # 登录与会话
  flow/        # 预约状态机
  priority/    # 院区/职称策略
  scheduler/   # 放号调度
  adapters/shqmxx/  # 齐脉页面适配
scripts/grab.py
config/example.yaml
openspec/changes/jy-wechat-appointment-grab/  # 规格与任务
```

## 说明与风险

- 微信 OAuth `code` 一次性，无法稳定“纯静默”伪造登录；首版为半自动会话复用。
- H5 改版会导致选择器失效，适配逻辑集中在 `src/robjy/adapters/shqmxx/`。
- 放号瞬时竞争激烈，不保证一定约到；失败时查看 `.data/artifacts/` 截图与日志。

## OpenSpec

规划变更：`openspec/changes/jy-wechat-appointment-grab/`。实现任务见其中 `tasks.md`。
