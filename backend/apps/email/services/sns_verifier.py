"""
SNS Signature Verifier
======================
Verify AWS SNS message signatures to prevent webhook spoofing.

CRITICAL: Always verify SNS signatures before processing webhook data.
"""

import base64
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

from apps.core.observability import get_logger

logger = get_logger(__name__)


class SNSSignatureVerifier:
    """
    Verify AWS SNS message signatures.

    Prevents attackers from spoofing bounce/complaint/delivery notifications.

    Security Checks:
        1. Certificate URL must be from amazonaws.com
        2. Certificate URL must use HTTPS
        3. Signature must be valid against the message content
    """

    # Cache certificates to avoid repeated downloads
    _cert_cache = {}

    @classmethod
    def verify(cls, message: dict) -> bool:
        """
        Verify SNS message signature.

        Args:
            message: Parsed JSON from SNS webhook

        Returns:
            True if signature is valid

        Raises:
            ValueError: If signature verification fails
        """
        # Validate certificate URL is from AWS
        cert_url = message.get('SigningCertURL', '')
        parsed = urlparse(cert_url)

        if not parsed.hostname or not parsed.hostname.endswith('.amazonaws.com'):
            raise ValueError("Certificate URL not from AWS")

        if parsed.scheme != 'https':
            raise ValueError("Certificate URL must be HTTPS")

        # Get certificate (cached)
        cert = cls._get_certificate(cert_url)

        # Build string to sign based on message type
        msg_type = message.get('Type', '')
        if msg_type == 'Notification':
            string_to_sign = cls._build_notification_string(message)
        elif msg_type in ('SubscriptionConfirmation', 'UnsubscribeConfirmation'):
            string_to_sign = cls._build_subscription_string(message)
        else:
            raise ValueError(f"Unknown message type: {msg_type}")

        # Verify signature
        signature = base64.b64decode(message['Signature'])
        public_key = cert.public_key()

        try:
            public_key.verify(
                signature,
                string_to_sign.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA1()  # SNS uses SHA1
            )
            return True
        except Exception as e:
            logger.warning("sns.signature_verification_failed", error=str(e))
            raise ValueError("Invalid SNS signature")

    @classmethod
    def _get_certificate(cls, url: str):
        """
        Get and cache certificate from URL.

        Args:
            url: Certificate URL

        Returns:
            X509 certificate object
        """
        if url not in cls._cert_cache:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                cls._cert_cache[url] = load_pem_x509_certificate(
                    response.content
                )
            except Exception as e:
                logger.error("sns.certificate_fetch_failed", url=url, error=str(e))
                raise ValueError(f"Failed to fetch certificate: {e}")

        return cls._cert_cache[url]

    @staticmethod
    def _build_notification_string(msg: dict) -> str:
        """
        Build the string to sign for Notification messages.

        Fields must be in this exact order per AWS documentation.
        """
        parts = [
            'Message', msg.get('Message', ''),
            'MessageId', msg.get('MessageId', ''),
        ]

        # Subject is optional
        if 'Subject' in msg:
            parts.extend(['Subject', msg['Subject']])

        parts.extend([
            'Timestamp', msg.get('Timestamp', ''),
            'TopicArn', msg.get('TopicArn', ''),
            'Type', msg.get('Type', ''),
        ])

        return '\n'.join(parts) + '\n'

    @staticmethod
    def _build_subscription_string(msg: dict) -> str:
        """
        Build the string to sign for SubscriptionConfirmation messages.

        Fields must be in this exact order per AWS documentation.
        """
        return (
            f"Message\n{msg.get('Message', '')}\n"
            f"MessageId\n{msg.get('MessageId', '')}\n"
            f"SubscribeURL\n{msg.get('SubscribeURL', '')}\n"
            f"Timestamp\n{msg.get('Timestamp', '')}\n"
            f"Token\n{msg.get('Token', '')}\n"
            f"TopicArn\n{msg.get('TopicArn', '')}\n"
            f"Type\n{msg.get('Type', '')}\n"
        )
