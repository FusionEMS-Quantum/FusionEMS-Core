from __future__ import annotations

import contextlib
import io
import logging
import stat
from dataclasses import dataclass
from typing import Any

import paramiko

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OfficeAllySftpConfig:
    host: str
    port: int
    username: str
    password: str
    remote_dir: str = "/"
    inbound_dir: str = "/inbound"
    era_dir: str = "/era"
    eligibility_dir: str = "/eligibility"
    claim_status_dir: str = "/claim_status"


class OfficeAllyClientError(RuntimeError):
    pass


def _validate_config(cfg: OfficeAllySftpConfig) -> None:
    if not cfg.host or not cfg.username or not cfg.password:
        raise OfficeAllyClientError("office_ally_sftp_not_configured")


def _connect(cfg: OfficeAllySftpConfig) -> tuple[paramiko.Transport, paramiko.SFTPClient]:
    """Open SFTP transport + client. Caller must close both."""
    _validate_config(cfg)
    transport = paramiko.Transport((cfg.host, cfg.port))
    try:
        transport.connect(username=cfg.username, password=cfg.password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        if sftp is None:
            raise OfficeAllyClientError("sftp_client_init_failed")
        return transport, sftp
    except Exception:
        with contextlib.suppress(Exception):
            transport.close()
        raise


def submit_837_via_sftp(*, cfg: OfficeAllySftpConfig, file_name: str, x12_bytes: bytes) -> str:
    """
    Uploads an 837 X12 file to an SFTP server (Office Ally-style connectivity).
    Returns the remote path uploaded.
    """
    transport, sftp = _connect(cfg)
    try:
        remote_path = f"{cfg.remote_dir.rstrip('/')}/{file_name}"
        with io.BytesIO(x12_bytes) as bio:
            sftp.putfo(bio, remote_path)
        return remote_path
    finally:
        with contextlib.suppress(Exception):
            sftp.close()
        with contextlib.suppress(Exception):
            transport.close()


def retrieve_sftp_files(
    *,
    cfg: OfficeAllySftpConfig,
    remote_dir: str,
    prefix_filter: str = "",
    max_files: int = 100,
) -> list[dict[str, Any]]:
    """
    Lists and downloads X12 response files from a remote SFTP directory.
    Returns list of {filename, content, size_bytes} dicts.
    Files are NOT deleted after retrieval — caller decides archive strategy.
    """
    transport, sftp = _connect(cfg)
    results: list[dict[str, Any]] = []
    try:
        entries = sftp.listdir_attr(remote_dir)
        filtered = [
            e for e in entries
            if stat.S_ISREG(e.st_mode or 0)
            and (not prefix_filter or (e.filename or "").startswith(prefix_filter))
        ]
        filtered.sort(key=lambda e: e.st_mtime or 0, reverse=True)

        for entry in filtered[:max_files]:
            remote_path = f"{remote_dir.rstrip('/')}/{entry.filename}"
            buf = io.BytesIO()
            sftp.getfo(remote_path, buf)
            content = buf.getvalue()
            results.append({
                "filename": entry.filename,
                "content": content.decode("utf-8", errors="replace"),
                "size_bytes": len(content),
            })
        return results
    finally:
        with contextlib.suppress(Exception):
            sftp.close()
        with contextlib.suppress(Exception):
            transport.close()


def poll_eligibility_responses(
    *,
    cfg: OfficeAllySftpConfig,
    max_files: int = 50,
) -> list[dict[str, Any]]:
    """
    Poll for 271 eligibility response files from the clearinghouse.
    Returns list of {filename, content, size_bytes}.
    """
    logger.info("polling_eligibility_responses dir=%s", cfg.eligibility_dir)
    return retrieve_sftp_files(
        cfg=cfg,
        remote_dir=cfg.eligibility_dir,
        prefix_filter="271",
        max_files=max_files,
    )


def poll_claim_status_responses(
    *,
    cfg: OfficeAllySftpConfig,
    max_files: int = 50,
) -> list[dict[str, Any]]:
    """
    Poll for 277 claim status response files from the clearinghouse.
    Returns list of {filename, content, size_bytes}.
    """
    logger.info("polling_claim_status_responses dir=%s", cfg.claim_status_dir)
    return retrieve_sftp_files(
        cfg=cfg,
        remote_dir=cfg.claim_status_dir,
        prefix_filter="277",
        max_files=max_files,
    )


def poll_era_files(
    *,
    cfg: OfficeAllySftpConfig,
    max_files: int = 50,
) -> list[dict[str, Any]]:
    """
    Poll for 835 ERA (Electronic Remittance Advice) files from the clearinghouse.
    Returns list of {filename, content, size_bytes}.
    """
    logger.info("polling_era_files dir=%s", cfg.era_dir)
    return retrieve_sftp_files(
        cfg=cfg,
        remote_dir=cfg.era_dir,
        prefix_filter="835",
        max_files=max_files,
    )


def submit_270_eligibility_inquiry(
    *,
    cfg: OfficeAllySftpConfig,
    file_name: str,
    x12_bytes: bytes,
) -> str:
    """
    Uploads a 270 eligibility inquiry to the clearinghouse outbound directory.
    Returns the remote path uploaded.
    """
    transport, sftp = _connect(cfg)
    try:
        remote_path = f"{cfg.remote_dir.rstrip('/')}/{file_name}"
        with io.BytesIO(x12_bytes) as bio:
            sftp.putfo(bio, remote_path)
        logger.info("submitted_270_eligibility file=%s", file_name)
        return remote_path
    finally:
        with contextlib.suppress(Exception):
            sftp.close()
        with contextlib.suppress(Exception):
            transport.close()


def submit_276_claim_status_inquiry(
    *,
    cfg: OfficeAllySftpConfig,
    file_name: str,
    x12_bytes: bytes,
) -> str:
    """
    Uploads a 276 claim status inquiry to the clearinghouse outbound directory.
    Returns the remote path uploaded.
    """
    transport, sftp = _connect(cfg)
    try:
        remote_path = f"{cfg.remote_dir.rstrip('/')}/{file_name}"
        with io.BytesIO(x12_bytes) as bio:
            sftp.putfo(bio, remote_path)
        logger.info("submitted_276_claim_status file=%s", file_name)
        return remote_path
    finally:
        with contextlib.suppress(Exception):
            sftp.close()
        with contextlib.suppress(Exception):
            transport.close()
