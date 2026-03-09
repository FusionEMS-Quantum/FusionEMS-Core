import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from core_app.models.growth_models import (
    ConversionEvent, LeadScore, Proposal, GrowthCampaign,
    GrowthSocialPost, GrowthDemoAsset, GrowthLandingPage, GrowthAutomation
)

def utc_now():
    return datetime.now(timezone.utc)

class AIGrowthService:
    def __init__(self, db: Session):
        self.db = db

    def record_conversion_event(self, funnel_stage: str, event_type: str, session_id: str, metadata: Dict[str, Any]) -> ConversionEvent:
        event = ConversionEvent(
            id=str(uuid.uuid4()),
            funnel_stage=funnel_stage,
            event_type=event_type,
            session_id=session_id,
            event_metadata=metadata,
            created_at=utc_now()
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        self.score_lead_pipeline(session_id, metadata)
        return event

    def score_lead_pipeline(self, session_id: str, metadata: Dict[str, Any]):
        email = metadata.get("email")
        if not email:
            return
        
        # Check if lead exists
        stmt = select(LeadScore).where(LeadScore.contact_email == email)
        lead = self.db.execute(stmt).scalar_one_or_none()
        
        if not lead:
            lead = LeadScore(
                id=str(uuid.uuid4()),
                contact_email=email,
                agency_name=metadata.get("agency_name", "Unknown Agency"),
                zip_code=metadata.get("zip_code", ""),
                call_volume=metadata.get("call_volume", 0),
                score=10.0,
                tier="low",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            self.db.add(lead)
        else:
            # Simple scoring logic
            lead.score = (lead.score or 0.0) + 15.0
            if lead.score > 80:
                lead.tier = "hot"
            elif lead.score > 50:
                lead.tier = "warm"
            else:
                lead.tier = "low"
            lead.updated_at = utc_now()
        
        self.db.commit()

    def create_campaign(self, name: str, objective: str, audience: Dict[str, Any]) -> GrowthCampaign:
        camp = GrowthCampaign(
            id=str(uuid.uuid4()),
            name=name,
            status="draft",
            objective=objective,
            audience=audience,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        self.db.add(camp)
        self.db.commit()
        self.db.refresh(camp)
        self.generate_content_for_campaign(camp.id)
        return camp

    def generate_content_for_campaign(self, campaign_id: str):
        # AI Content Engine Mock/Stub logic mapped to DB
        platforms = ["LinkedIn", "X", "Email"]
        for p in platforms:
            post = GrowthSocialPost(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                platform=p,
                content=f"Generated AI content for {p} promoting EMS platform reliability and billing automation.",
                status="draft",
                created_at=utc_now()
            )
            self.db.add(post)
        
        self.db.commit()

    def generate_demo_assets(self, campaign_id: str, focus_area: str):
        # AI Demo Engine logic mapping
        asset = GrowthDemoAsset(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            asset_type="script",
            content_url="",
            asset_metadata={
                "focus": focus_area,
                "script": f"This 60-second clip shows the new {focus_area} flow in FusionEMS...",
                "scenes": [
                    {"time": "0-10s", "visual": "Dashboard", "voiceover": "Welcome to FusionEMS."},
                    {"time": "10-40s", "visual": "Action", "voiceover": f"Here is how you handle {focus_area}."}
                ]
            },
            created_at=utc_now()
        )
        self.db.add(asset)
        self.db.commit()

    def launch_orchestrator(self, mode: str) -> Dict[str, Any]:
        return {
            "run_id": str(uuid.uuid4()),
            "mode": mode,
            "status": "started",
            "queued_sync_jobs": 5,
            "blocked_items": []
        }
