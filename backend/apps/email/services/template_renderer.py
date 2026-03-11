"""
Template Renderer
=================
Renders email templates with context variables.
"""

from django.template import Template, Context, TemplateSyntaxError

# Observability
from apps.core.observability import get_logger

logger = get_logger(__name__)


class TemplateRenderer:
    """
    Render email templates with context variables.

    Uses Django's template engine for {{ variable }} syntax.
    Auto-generates plain text from HTML if not provided.
    """

    @staticmethod
    def render(template, context: dict) -> dict:
        """
        Render template with context.

        Args:
            template: EmailTemplate instance
            context: Dictionary of variables

        Returns:
            {
                'subject': str,
                'html_body': str,
                'text_body': str
            }

        Raises:
            TemplateSyntaxError: If template has syntax errors
        """
        django_context = Context(context)

        try:
            # Render subject
            subject_template = Template(template.subject)
            subject = subject_template.render(django_context)

            # Render HTML body
            html_template = Template(template.html_body)
            html_body = html_template.render(django_context)

            # Render or generate text body
            if template.text_body:
                text_template = Template(template.text_body)
                text_body = text_template.render(django_context)
            else:
                # Auto-generate from HTML
                text_body = TemplateRenderer._html_to_text(html_body)

            return {
                'subject': subject.strip(),
                'html_body': html_body,
                'text_body': text_body.strip()
            }

        except TemplateSyntaxError as e:
            logger.error(
                "email.template.syntax_error",
                template_name=template.name,
                error=str(e),
            )
            raise

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML to plain text.

        Uses html2text library for smart conversion.
        Falls back to basic stripping if html2text unavailable.
        """
        try:
            from html2text import html2text
            return html2text(html)
        except ImportError:
            # Fallback: basic HTML stripping
            import re
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html)
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
