import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String

from core_app.db.base import Base


def utc_now():
    return datetime.now(UTC)

def generate_uuid():
    return str(uuid.uuid4())

class ROIFunnelScenario(Base):
    __tablename__ = "roi_funnel_scenarios"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    agency_name = Column(String, index=True)
    inputs = Column(JSON, default=dict)
    outputs = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    funnel_stage = Column(String, index=True)
    event_type = Column(String, index=True)
    session_id = Column(String, index=True)
    event_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class LeadScore(Base):
    __tablename__ = "lead_scores"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    agency_name = Column(String)
    contact_email = Column(String, index=True)
    zip_code = Column(String)
    call_volume = Column(Integer)
    score = Column(Float)
    tier = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    roi_scenario_id = Column(String, index=True)
    agency_name = Column(String)
    contact_name = Column(String)
    status = Column(String, index=True)
    modules = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class BAASignature(Base):
    __tablename__ = "baa_signatures"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    signer_name = Column(String)
    signer_email = Column(String, index=True)
    signer_title = Column(String)
    ip_address = Column(String)
    agreed_at = Column(DateTime(timezone=True), default=utc_now)

class ROIShareLink(Base):
    __tablename__ = "roi_share_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    scenario_id = Column(String, index=True)
    share_token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utc_now)

class GrowthCampaign(Base):
    __tablename__ = "growth_campaigns"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, index=True)
    status = Column(String, index=True) # draft, active, paused, completed
    objective = Column(String)
    audience = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class GrowthSocialPost(Base):
    __tablename__ = "growth_social_posts"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    campaign_id = Column(String, ForeignKey("growth_campaigns.id"))
    platform = Column(String, index=True)
    content = Column(String)
    media_urls = Column(JSON, default=list)
    scheduled_for = Column(DateTime(timezone=True))
    status = Column(String, index=True) # queued, published, failed, draft
    post_metrics = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class GrowthDemoAsset(Base):
    __tablename__ = "growth_demo_assets"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    campaign_id = Column(String, ForeignKey("growth_campaigns.id"), nullable=True)
    asset_type = Column(String) # script, video, screenshot
    content_url = Column(String)
    asset_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class GrowthLandingPage(Base):
    __tablename__ = "growth_landing_pages"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    slug = Column(String, unique=True, index=True)
    campaign_id = Column(String, ForeignKey("growth_campaigns.id"), nullable=True)
    title = Column(String)
    config = Column(JSON, default=dict)
    status = Column(String, index=True) # draft, published
    views = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class GrowthAutomation(Base):
    __tablename__ = "growth_automations"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String)
    trigger_type = Column(String)
    flow_schema = Column(JSON, default=dict)
    status = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
