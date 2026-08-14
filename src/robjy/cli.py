from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from robjy.config import load_config
from robjy.flow.booking import BookingFlow
from robjy.logging_utils import setup_logging
from robjy.scheduler.release import ReleaseScheduler
from robjy.session.browser import BrowserSession, SessionExpiredError
from robjy.session.cookies import import_cookie_text

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="robjy-grab",
        description="九院齐脉 H5 门诊预约辅助（仅限本人合法就医用途）",
    )
    p.add_argument(
        "-c",
        "--config",
        default="config/local.yaml",
        help="配置文件路径（默认 config/local.yaml，可从 example.yaml 复制）",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")

    sub = p.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="有头浏览器完成微信授权并导出 storage_state")
    login.add_argument("--wait-sec", type=int, default=180, help="等待授权秒数")

    once = sub.add_parser("once", help="立即执行一次预约流程（调试/非放号窗口）")
    once.add_argument(
        "--stop-before-captcha",
        action="store_true",
        help="跑到验证码前停止（不下单）",
    )
    once.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖配置中的 headless",
    )

    sched = sub.add_parser("schedule", help="按配置在 07:30 放号窗口热身并轮询抢号")
    sched.add_argument(
        "--stop-before-captcha",
        action="store_true",
        help="跑到验证码前停止（不下单）",
    )
    sched.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖配置中的 headless",
    )

    imp = sub.add_parser(
        "import-cookie",
        help="从 Charles Cookie 头/文本生成 Playwright storage_state",
    )
    imp.add_argument(
        "--cookie",
        help="Cookie 原文（推荐 Headers 里的 Cookie 整行）；也可用 --cookie-file",
    )
    imp.add_argument(
        "--cookie-file",
        help="从文件读取 Cookie 原文（避免把密钥写进 shell history）",
    )
    imp.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出路径（默认用配置里的 session.state_path）",
    )
    imp.add_argument(
        "--domain",
        default=".shqmxx.com",
        help="Cookie domain（默认 .shqmxx.com）",
    )

    return p


def cmd_login(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    setup_logging(
        logging.DEBUG if args.verbose else logging.INFO,
        cfg.artifact_dir / "robjy.log",
    )
    with BrowserSession(cfg) as session:
        path = session.login_interactive(wait_sec=args.wait_sec)
        print(f"会话已保存: {path}")
    return 0


def cmd_once(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    setup_logging(
        logging.DEBUG if args.verbose else logging.INFO,
        cfg.artifact_dir / "robjy.log",
    )
    headless = cfg.session.headless if args.headless is None else args.headless
    with BrowserSession(cfg) as session:
        session.open_with_state(headless=headless)
        flow = BookingFlow(
            cfg,
            session,
            stop_before_captcha=args.stop_before_captcha,
        )
        result = flow.run()
        print(
            f"结果: ok={result.ok} state={result.state.value} "
            f"campus={result.campus} doctor={result.doctor} msg={result.message}"
        )
        if result.artifacts:
            print("产物:")
            for a in result.artifacts:
                print(f"  - {a}")
        return 0 if result.ok else 2


def cmd_schedule(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    setup_logging(
        logging.DEBUG if args.verbose else logging.INFO,
        cfg.artifact_dir / "robjy.log",
    )
    headless = cfg.session.headless if args.headless is None else args.headless
    with BrowserSession(cfg) as session:
        session.open_with_state(headless=headless)
        session.ensure_authenticated()
        scheduler = ReleaseScheduler(cfg, session)
        outcome = scheduler.run_scheduled(stop_before_captcha=args.stop_before_captcha)
        summary = ReleaseScheduler.summarize(outcome)
        print(summary)
        logger.info("调度汇总: %s", summary)
        return 0 if outcome.result.ok else 2


def cmd_import_cookie(args: argparse.Namespace) -> int:
    raw = args.cookie
    if args.cookie_file:
        raw = Path(args.cookie_file).read_text(encoding="utf-8")
    if not raw or not str(raw).strip():
        print("请提供 --cookie 或 --cookie-file", file=sys.stderr)
        return 1

    output = args.output
    if output is None:
        cfg_path = Path(args.config)
        if cfg_path.exists():
            output = str(load_config(cfg_path).state_path)
        else:
            output = ".data/storage_state.json"

    path = import_cookie_text(str(raw), output, domain=args.domain)
    print(f"已写入 storage_state: {path}")
    print("下一步: python scripts/grab.py once -c config/local.yaml --stop-before-captcha --no-headless")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "login":
            return cmd_login(args)
        if args.command == "once":
            return cmd_once(args)
        if args.command == "schedule":
            return cmd_schedule(args)
        if args.command == "import-cookie":
            return cmd_import_cookie(args)
        parser.error(f"未知命令: {args.command}")
        return 1
    except SessionExpiredError as exc:
        print(f"会话错误: {exc}", file=sys.stderr)
        return 3
    except FileNotFoundError as exc:
        print(f"文件错误: {exc}", file=sys.stderr)
        return 4
    except ValueError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
