## 1. 工程脚手架

- [x] 1.1 初始化 Python 项目（`pyproject.toml` / `requirements.txt`），加入 Playwright、PyYAML、日志依赖
- [x] 1.2 创建包结构：`src/robjy/{session,flow,priority,scheduler,adapters/shqmxx}` 与 `scripts/grab.py`
- [x] 1.3 添加 `config/example.yaml`（入口 URL/CustomerId、科室、院区优先级、职称优先级、就诊人、07:30、轮询间隔、confirm_submit）
- [x] 1.4 更新 README：用途声明、合规说明、安装与首次登录步骤

## 2. H5 会话与模拟登录

- [x] 2.1 实现有头浏览器手动授权流程，导出 `storage_state` 到可配置路径
- [x] 2.2 实现无头/有头启动时注入 session state 并打开配置的 H5 入口
- [x] 2.3 实现登录态探测（姓名/医保卡等信号）与过期时明确失败提示
- [x] 2.4 补充 session 相关单元测试或最小集成冒烟脚本

## 3. 选择策略

- [x] 3.1 实现 `PriorityPolicy`：院区默认南部 → 高科；职称默认主任 → 副主任；可配置覆盖
- [x] 3.2 实现科室匹配（精确/包含）与未找到时报错
- [x] 3.3 实现同优先级候选的确定性 tie-break（最早可约日期/时段）
- [x] 3.4 为策略模块编写纯单测（不依赖真实页面）

## 4. 门诊预约流程状态机

- [x] 4.1 实现 `BookingFlow` 状态机骨架与逐步日志/截图落盘
- [x] 4.2 适配「门诊预约」入口导航
- [x] 4.3 适配预约须知：「是」→「我知道了」
- [x] 4.4 适配院区列表/切换与科室左右栏选择（对齐 selection-priority）
- [x] 4.5 适配医师列表、可约日期选择与点击「预约」
- [x] 4.6 适配时段弹层选择与点击「确认」
- [x] 4.7 适配就诊人确认
- [x] 4.8 适配验证码截图 + 终端输入 + 点击「预约」；支持 `confirm_submit` 门闩
- [x] 4.9 one-shot CLI 跑通（在非放号时段验证到验证码前或等价可测节点）

## 5. 放号调度

- [x] 5.1 实现 Asia/Shanghai 07:30 调度与可配置 lead-time 热身
- [x] 5.2 实现放号窗口内轮询发现号源，尊重最小间隔与最大尝试次数
- [x] 5.3 成功/超时/失败的终止条件与汇总日志
- [x] 5.4 CLI 支持 `--once` 与 `--schedule` 两种模式

## 6. 验收与收尾

- [x] 6.1 对照 specs 四条能力做场景 checklist 自测并记录结果
- [x] 6.2 清理示例中的敏感信息，确保 state/验证码截图路径在 `.gitignore`
- [x] 6.3 将 OpenSpec delta 保持与实现一致（若实现中调整行为则回写 design/tasks 勾选）
