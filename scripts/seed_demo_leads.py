"""Seed demo leads for local testing.

Usage:
  DATABASE_URL=postgresql+psycopg2://apple@localhost:5432/leadpulse \
  python scripts/seed_demo_leads.py
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models.lead import Lead, LeadPriority, LeadSource, LeadStage
from app.models.user import User
from app.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed demo leads for development/testing only."
    )
    parser.add_argument(
        "--dev-only-confirm",
        action="store_true",
        help="Required safety flag acknowledging this script is for development only.",
    )
    return parser.parse_args()


def ensure_dev_only_safe() -> None:
    database_url = get_settings().DATABASE_URL

    if database_url.startswith("sqlite"):
        return

    parsed = urlparse(database_url)
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.hostname not in local_hosts:
        raise RuntimeError(
            "Refusing to run demo seeding on a non-local database. "
            "Use localhost/127.0.0.1/::1 only."
        )


def demo_leads() -> list[dict]:
    today = date.today()
    return [
        {
            "title": "CRM Automation for Zenith Textiles",
            "company_name": "Zenith Textiles Pvt Ltd",
            "contact_name": "Aarav Sharma",
            "email": "aarav.sharma@zenithtextiles.in",
            "phone": "+919812345601",
            "stage": LeadStage.new,
            "priority": LeadPriority.high,
            "source": LeadSource.website,
            "value": Decimal("850000.00"),
            "notes": "Requested product walkthrough for sales ops team.",
            "expected_close_date": today + timedelta(days=35),
        },
        {
            "title": "Lead Management Setup for BluePeak Logistics",
            "company_name": "BluePeak Logistics",
            "contact_name": "Isha Verma",
            "email": "isha.verma@bluepeaklogistics.in",
            "phone": "+919812345602",
            "stage": LeadStage.contacted,
            "priority": LeadPriority.medium,
            "source": LeadSource.referral,
            "value": Decimal("640000.00"),
            "notes": "Initial discovery call done.",
            "expected_close_date": today + timedelta(days=28),
        },
        {
            "title": "Pipeline Revamp for Orion Foods",
            "company_name": "Orion Foods India",
            "contact_name": "Rohan Mehta",
            "email": "rohan.mehta@orionfoods.in",
            "phone": "+919812345603",
            "stage": LeadStage.qualified,
            "priority": LeadPriority.high,
            "source": LeadSource.cold_call,
            "value": Decimal("1200000.00"),
            "notes": "Qualified with approved budget.",
            "expected_close_date": today + timedelta(days=21),
        },
        {
            "title": "Sales Dashboard Rollout for Nimbus Retail",
            "company_name": "Nimbus Retail",
            "contact_name": "Kavya Nair",
            "email": "kavya.nair@nimbusretail.in",
            "phone": "+919812345604",
            "stage": LeadStage.proposal,
            "priority": LeadPriority.high,
            "source": LeadSource.email_campaign,
            "value": Decimal("990000.00"),
            "notes": "Proposal submitted with quarterly pricing.",
            "expected_close_date": today + timedelta(days=18),
        },
        {
            "title": "Territory Tracking for Trident Motors",
            "company_name": "Trident Motors",
            "contact_name": "Aditya Kulkarni",
            "email": "aditya.kulkarni@tridentmotors.in",
            "phone": "+919812345605",
            "stage": LeadStage.negotiation,
            "priority": LeadPriority.high,
            "source": LeadSource.trade_show,
            "value": Decimal("1500000.00"),
            "notes": "Negotiating multi-branch discount.",
            "expected_close_date": today + timedelta(days=12),
        },
        {
            "title": "Inside Sales Platform for Sunrise Pharma",
            "company_name": "Sunrise Pharma",
            "contact_name": "Neha Patel",
            "email": "neha.patel@sunrisepharma.in",
            "phone": "+919812345606",
            "stage": LeadStage.won,
            "priority": LeadPriority.medium,
            "source": LeadSource.social_media,
            "value": Decimal("730000.00"),
            "notes": "Deal signed this week.",
            "expected_close_date": today - timedelta(days=2),
        },
        {
            "title": "Lead Nurturing for Delta Buildcon",
            "company_name": "Delta Buildcon",
            "contact_name": "Siddharth Rao",
            "email": "siddharth.rao@deltabuildcon.in",
            "phone": "+919812345607",
            "stage": LeadStage.lost,
            "priority": LeadPriority.low,
            "source": LeadSource.other,
            "value": Decimal("410000.00"),
            "notes": "Moved to competitor due to procurement mandate.",
            "expected_close_date": today - timedelta(days=10),
        },
        {
            "title": "Customer Funnel Cleanup for AeroNova",
            "company_name": "AeroNova Systems",
            "contact_name": "Priya Singh",
            "email": "priya.singh@aeronova.in",
            "phone": "+919812345608",
            "stage": LeadStage.new,
            "priority": LeadPriority.medium,
            "source": LeadSource.website,
            "value": Decimal("560000.00"),
            "notes": "Inbound request via pricing page.",
            "expected_close_date": today + timedelta(days=40),
        },
        {
            "title": "Regional CRM Adoption for MetroMed",
            "company_name": "MetroMed Healthcare",
            "contact_name": "Vikram Joshi",
            "email": "vikram.joshi@metromed.in",
            "phone": "+919812345609",
            "stage": LeadStage.contacted,
            "priority": LeadPriority.low,
            "source": LeadSource.referral,
            "value": Decimal("300000.00"),
            "notes": "Awaiting stakeholder availability.",
            "expected_close_date": today + timedelta(days=30),
        },
        {
            "title": "Field Team Visibility for GreenArc Energy",
            "company_name": "GreenArc Energy",
            "contact_name": "Ananya Iyer",
            "email": "ananya.iyer@greenarcenergy.in",
            "phone": "+919812345610",
            "stage": LeadStage.qualified,
            "priority": LeadPriority.medium,
            "source": LeadSource.cold_call,
            "value": Decimal("820000.00"),
            "notes": "Qualified for pilot in two cities.",
            "expected_close_date": today + timedelta(days=25),
        },
        {
            "title": "Conversion Analytics for HexaFin",
            "company_name": "HexaFin Services",
            "contact_name": "Rahul Bansal",
            "email": "rahul.bansal@hexafin.in",
            "phone": "+919812345611",
            "stage": LeadStage.proposal,
            "priority": LeadPriority.high,
            "source": LeadSource.email_campaign,
            "value": Decimal("1110000.00"),
            "notes": "Proposal revised after legal review.",
            "expected_close_date": today + timedelta(days=16),
        },
        {
            "title": "Renewal Forecasting for CoralSoft",
            "company_name": "CoralSoft Technologies",
            "contact_name": "Meera Chawla",
            "email": "meera.chawla@coralsoft.in",
            "phone": "+919812345612",
            "stage": LeadStage.negotiation,
            "priority": LeadPriority.medium,
            "source": LeadSource.trade_show,
            "value": Decimal("680000.00"),
            "notes": "Commercials under procurement discussion.",
            "expected_close_date": today + timedelta(days=9),
        },
        {
            "title": "Omnichannel Tracking for UrbanKart",
            "company_name": "UrbanKart",
            "contact_name": "Nikhil Gupta",
            "email": "nikhil.gupta@urbankart.in",
            "phone": "+919812345613",
            "stage": LeadStage.won,
            "priority": LeadPriority.high,
            "source": LeadSource.social_media,
            "value": Decimal("1320000.00"),
            "notes": "Signed annual plan with add-on module.",
            "expected_close_date": today - timedelta(days=1),
        },
        {
            "title": "Deal Room Setup for PrimeForge",
            "company_name": "PrimeForge Manufacturing",
            "contact_name": "Tanvi Deshpande",
            "email": "tanvi.deshpande@primeforge.in",
            "phone": "+919812345614",
            "stage": LeadStage.lost,
            "priority": LeadPriority.medium,
            "source": LeadSource.other,
            "value": Decimal("760000.00"),
            "notes": "Project deferred to next financial year.",
            "expected_close_date": today - timedelta(days=8),
        },
        {
            "title": "Sales Ops Digitization for NovaAgri",
            "company_name": "NovaAgri Solutions",
            "contact_name": "Arjun Reddy",
            "email": "arjun.reddy@novaagri.in",
            "phone": "+919812345615",
            "stage": LeadStage.new,
            "priority": LeadPriority.low,
            "source": LeadSource.website,
            "value": Decimal("450000.00"),
            "notes": "Requested multilingual workflow support.",
            "expected_close_date": today + timedelta(days=45),
        },
    ]


def seed_demo_leads() -> None:
    with SessionLocal() as db:
        users = db.execute(select(User).where(User.is_active.is_(True))).scalars().all()
        if not users:
            raise RuntimeError("No active users found. Create at least one user before seeding leads.")

        payload = demo_leads()
        for idx, item in enumerate(payload):
            assignee = users[idx % len(users)]
            creator = users[0]

            lead = Lead(
                title=item["title"],
                company_name=item["company_name"],
                contact_name=item["contact_name"],
                email=item["email"],
                phone=item["phone"],
                stage=item["stage"],
                priority=item["priority"],
                source=item["source"],
                value=item["value"],
                notes=item["notes"],
                expected_close_date=item["expected_close_date"],
                assigned_to_id=assignee.id,
                created_by_id=creator.id,
            )
            db.add(lead)

        db.commit()

    print("Inserted 15 demo leads across all pipeline stages.")


if __name__ == "__main__":
    args = parse_args()
    if not args.dev_only_confirm:
        raise SystemExit(
            "Demo seeding is restricted to development usage. "
            "Re-run with --dev-only-confirm."
        )

    ensure_dev_only_safe()
    seed_demo_leads()
