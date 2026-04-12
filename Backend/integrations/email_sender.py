from __future__ import annotations

import argparse
import smtplib
import ssl
import re
import sys
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable


def _ensure_repo_root_on_path_for_direct_run() -> None:
    """Allow direct file execution without breaking package imports."""
    if __package__ not in (None, ""):
        return
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_path_for_direct_run()

if __package__ in (None, ""):
    from Backend.settings import EmailSettings, Settings, get_email_settings, get_settings
else:
    from ..settings import EmailSettings, Settings, get_email_settings, get_settings


DEBUG_DEFAULT_SUBJECT = "XIEXin backend test email"
DEBUG_DEFAULT_BODY = "This is a test email sent by Backend.integrations.email_sender."
_AI_AGENT_EMAIL_FOOTER = "——本邮件为AI agent发出（来源xiexin1.gd）"


class EmailSenderError(RuntimeError):
    """Structured email sender error for backend integrations."""


_EMAIL_ADDRESS_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_RECEIVER_SPLIT_RE = re.compile(r"[\s,，;；]+")


def _normalize_receiver_input(receiver: str | Iterable[str] | None) -> list[str]:
    if receiver is None:
        return []

    if isinstance(receiver, str):
        candidates = [item.strip() for item in _RECEIVER_SPLIT_RE.split(receiver) if item.strip()]
    else:
        candidates = []
        for item in receiver:
            candidates.extend(_normalize_receiver_input(str(item or "")))

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(normalized)
    return unique_candidates


def _resolve_receivers(receiver: str | Iterable[str] | None, email_settings: EmailSettings) -> list[str]:
    resolved_receivers = _normalize_receiver_input(receiver)
    if not resolved_receivers:
        resolved_receivers = _normalize_receiver_input(email_settings.default_receiver)
    if not resolved_receivers:
        raise EmailSenderError(
            "Missing email receiver. Pass receiver explicitly or set EMAIL_DEFAULT_RECEIVER."
        )
    for resolved_receiver in resolved_receivers:
        if _EMAIL_ADDRESS_RE.fullmatch(resolved_receiver):
            continue
        raise EmailSenderError(
            f"Invalid receiver email address: {resolved_receiver}. Please provide a full email like user@example.com."
        )
    return resolved_receivers


def _validate_email_settings(email_settings: EmailSettings) -> None:
    if not email_settings.enabled:
        raise EmailSenderError("Email sending is disabled. Set EMAIL_ENABLED=true first.")
    if not (email_settings.sender or "").strip():
        raise EmailSenderError("Missing EMAIL_SENDER.")
    if not (email_settings.auth_code or "").strip():
        raise EmailSenderError("Missing EMAIL_AUTH_CODE.")
    if not (email_settings.smtp_host or "").strip():
        raise EmailSenderError("Missing EMAIL_SMTP_HOST.")
    if int(email_settings.smtp_port) <= 0:
        raise EmailSenderError("EMAIL_SMTP_PORT must be a positive integer.")
    if email_settings.use_ssl and email_settings.use_starttls:
        raise EmailSenderError("EMAIL_USE_SSL and EMAIL_USE_STARTTLS cannot both be true.")


def _build_message(*, sender: str, receiver: str, subject: str, body: str) -> MIMEText:
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    return msg


def _append_agent_footer(body: str) -> str:
    normalized_body = (body or "").rstrip()
    if normalized_body.endswith(_AI_AGENT_EMAIL_FOOTER):
        return normalized_body
    if not normalized_body:
        return _AI_AGENT_EMAIL_FOOTER
    return f"{normalized_body}\n\n{_AI_AGENT_EMAIL_FOOTER}"


def send_text_email(
    *,
    subject: str,
    body: str,
    receiver: str | Iterable[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, str | int | bool | list[str]]:
    """Send a plain text email using SMTP settings from environment/.env."""
    resolved_settings = settings or get_settings()
    email_settings = get_email_settings(resolved_settings)
    _validate_email_settings(email_settings)

    sender = str(email_settings.sender).strip()
    auth_code = str(email_settings.auth_code).strip()
    smtp_host = str(email_settings.smtp_host).strip()
    smtp_port = int(email_settings.smtp_port)
    timeout_seconds = float(email_settings.timeout_seconds)
    resolved_receivers = _resolve_receivers(receiver, email_settings)
    resolved_receiver_display = ", ".join(resolved_receivers)
    final_body = _append_agent_footer(body)
    message = _build_message(
        sender=sender,
        receiver=resolved_receiver_display,
        subject=(subject or "").strip(),
        body=final_body,
    )

    try:
        if email_settings.use_ssl:
            with smtplib.SMTP_SSL(
                smtp_host,
                smtp_port,
                timeout=timeout_seconds,
                context=ssl.create_default_context(),
            ) as server:
                server.login(sender, auth_code)
                server.sendmail(sender, resolved_receivers, message.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout_seconds) as server:
                if email_settings.use_starttls:
                    server.starttls(context=ssl.create_default_context())
                server.login(sender, auth_code)
                server.sendmail(sender, resolved_receivers, message.as_string())
    except (TimeoutError, OSError, smtplib.SMTPException, UnicodeEncodeError) as exc:
        raise EmailSenderError(f"Failed to send email via SMTP: {exc}") from exc

    return {
        "ok": True,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "receiver": resolved_receiver_display,
        "receivers": resolved_receivers,
        "subject": (subject or "").strip(),
        "transport": "ssl" if email_settings.use_ssl else "starttls" if email_settings.use_starttls else "plain",
    }


class EmailSender:
    """Facade class for backend email sending."""

    @staticmethod
    def send_text(
        *,
        subject: str,
        body: str,
        receiver: str | Iterable[str] | None = None,
        settings: Settings | None = None,
    ) -> dict[str, str | int | bool | list[str]]:
        return send_text_email(
            subject=subject,
            body=body,
            receiver=receiver,
            settings=settings,
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a plain text email using backend SMTP settings.")
    parser.add_argument("--receiver", default="", help="Optional receiver email; falls back to EMAIL_DEFAULT_RECEIVER.")
    parser.add_argument("--subject", default=DEBUG_DEFAULT_SUBJECT, help="Email subject.")
    parser.add_argument("--body", default=DEBUG_DEFAULT_BODY, help="Email body.")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    result = send_text_email(
        subject=args.subject,
        body=args.body,
        receiver=args.receiver or None,
    )
    print(f"Email sent successfully: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())