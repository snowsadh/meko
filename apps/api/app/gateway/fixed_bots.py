from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class FixedBot:
    name: str
    role: str
    employee_type: str
    description: str
    client_id: str
    client_secret: str
    app_token: str

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.app_token)


def _build_registry() -> dict[str, FixedBot]:
    return {
        "hr": FixedBot(
            name="Alison",
            role="HR Specialist",
            employee_type="hr",
            description="Manages onboarding, benefits, policies, and employee questions",
            client_id=settings.slack_bot_hr_client_id,
            client_secret=settings.slack_bot_hr_client_secret,
            app_token=settings.slack_bot_hr_app_token,
        ),
        "support": FixedBot(
            name="Alex",
            role="Customer Support Specialist",
            employee_type="support",
            description="Handles customer inquiries, support tickets, and troubleshooting",
            client_id=settings.slack_bot_support_client_id,
            client_secret=settings.slack_bot_support_client_secret,
            app_token=settings.slack_bot_support_app_token,
        ),
        "sales": FixedBot(
            name="Marcus",
            role="Sales Representative",
            employee_type="sales",
            description="Qualifies leads, researches prospects, and tracks pipeline metrics",
            client_id=settings.slack_bot_sales_client_id,
            client_secret=settings.slack_bot_sales_client_secret,
            app_token=settings.slack_bot_sales_app_token,
        ),
        "general": FixedBot(
            name="Jordan",
            role="General Assistant",
            employee_type="general",
            description="Versatile assistant for research, calculations, and general tasks",
            client_id=settings.slack_bot_general_client_id,
            client_secret=settings.slack_bot_general_client_secret,
            app_token=settings.slack_bot_general_app_token,
        ),
        "legal-compliance": FixedBot(
            name="Taylor",
            role="Legal & Compliance Officer",
            employee_type="legal-compliance",
            description="Reviews contracts, policies, and regulatory documents",
            client_id=settings.slack_bot_legal_client_id,
            client_secret=settings.slack_bot_legal_client_secret,
            app_token=settings.slack_bot_legal_app_token,
        ),
    }


FIXED_BOTS: dict[str, FixedBot] = _build_registry()


def get_fixed_bot(employee_type: str) -> FixedBot | None:
    return FIXED_BOTS.get(employee_type)
