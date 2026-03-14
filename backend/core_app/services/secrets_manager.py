from __future__ import annotations

import json
import logging
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# Ordered list of JSON key names to probe when the secret value is a JSON blob.
_API_KEY_CANDIDATES: tuple[str, ...] = (
    "api_key",
    "apikey",
    "key",
    "UMLS_API_KEY",
    "umls_api_key",
)


class SecretsManagerError(RuntimeError):
    """Raised when AWS Secrets Manager retrieval fails."""


@lru_cache(maxsize=64)
def get_secret_string(*, secret_id: str, region: str) -> str:
    """Retrieve a plaintext secret from AWS Secrets Manager.

    Results are cached per (secret_id, region) pair for the process lifetime
    to avoid repeated round-trips on hot paths. The cache is deliberately
    *not* invalidated on rotation — callers that need rotation awareness must
    clear the cache explicitly via ``get_secret_string.cache_clear()``.

    Args:
        secret_id: The secret name or full ARN.
        region:    AWS region (e.g. ``"us-east-1"``).

    Returns:
        The ``SecretString`` value as a plain Python string.

    Raises:
        SecretsManagerError: when the secret cannot be retrieved or has no
            ``SecretString`` (binary-only secrets are not supported).
    """
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except ClientError as exc:
        raise SecretsManagerError(
            f"Failed to retrieve secret '{secret_id}': {exc}"
        ) from exc
    except BotoCoreError as exc:
        raise SecretsManagerError(
            f"BotoCoreError retrieving secret '{secret_id}': {exc}"
        ) from exc

    secret = response.get("SecretString")
    if secret is None:
        raise SecretsManagerError(
            f"Secret '{secret_id}' has no SecretString "
            "(binary secrets are not supported)"
        )
    return secret


def extract_api_key(secret_string: str) -> str:
    """Extract a single API key value from a raw or JSON secret string.

    Accepts two formats:
    - **Plain string**: the secret value is the key itself — returned as-is
      after stripping whitespace.
    - **JSON object**: the first matching key from ``_API_KEY_CANDIDATES``
      is returned.

    Args:
        secret_string: The raw ``SecretString`` from Secrets Manager, or any
            plain string representing the key.

    Returns:
        The extracted API key string.

    Raises:
        ValueError: when the input is empty or is a JSON object that lacks
            any recognised API key field.
    """
    value = secret_string.strip()
    if not value:
        raise ValueError("Secret string is empty")

    if not value.startswith("{"):
        return value

    try:
        obj: dict = json.loads(value)
    except json.JSONDecodeError:
        # Not valid JSON — treat the whole string as the key
        return value

    for candidate in _API_KEY_CANDIDATES:
        if candidate in obj and obj[candidate]:
            return str(obj[candidate]).strip()

    raise ValueError(
        f"JSON secret does not contain a recognised API key field "
        f"(tried: {', '.join(_API_KEY_CANDIDATES)})"
    )
