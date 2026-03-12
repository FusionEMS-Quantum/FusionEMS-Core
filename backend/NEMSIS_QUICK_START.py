"""
NEMSIS Integration Quick Start

This shows how to integrate the NEMSIS API routes into your FastAPI application.
"""

# In backend/core_app/main.py (or your FastAPI app factory):

from fastapi import FastAPI
from core_app.api import nemsis_routes

def create_app() -> FastAPI:
    app = FastAPI(title="FusionEMS Core")
    
    # Include NEMSIS routes
    app.include_router(nemsis_routes.router)
    
    # ... other routes and middleware ...
    
    return app


# If you need to use the NEMSIS service in other parts of the application:

from core_app.nemsis.submission_service import NEMSISSubmissionService
from core_app.nemsis.production_client import NEMSISProductionClient

# Create service instance (usually once, at startup)
nemsis_client = NEMSISProductionClient()
submission_service = NEMSISSubmissionService(nemsis_client)


# Example: In a background worker submitting scheduled exports

async def export_ems_data_to_nemsis():
    """Scheduled task to export EMS data to NEMSIS daily."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Get EMS data as XML
    ems_xml = get_ems_export_xml()  # Your export logic
    
    try:
        result = await submission_service.submit_ems_data(
            xml_bytes=ems_xml,
            organization=get_org_nemsis_code(),
            username=get_org_nemsis_username(),
            password=get_org_nemsis_password(),
            schema_version="3.5.1",
            additional_info="Daily EMS export - " + datetime.utcnow().isoformat(),
        )
        
        logger.info(
            "ems_export_submitted",
            extra={
                "handle": result.request_handle,
                "status": result.status_code,
                "async": result.is_async,
            },
        )
        
        # If async, poll for results
        if result.is_async:
            # Could use background job queue here
            await submission_service.wait_for_submission(
                request_handle=result.request_handle,
                organization=get_org_nemsis_code(),
                username=get_org_nemsis_username(),
                password=get_org_nemsis_password(),
                max_wait_seconds=3600,  # 1 hour
            )
            
    except Exception as exc:
        logger.error(f"EMS export failed: {exc}")
        # Alert operations team


# Example: In a CLI command for testing submissions

import asyncio
import sys
from pathlib import Path

async def cli_submit_nemsis_data(xml_file: str, dataset_type: str):
    """CLI: Submit NEMSIS data for testing."""
    xml_path = Path(xml_file)
    if not xml_path.exists():
        print(f"Error: {xml_file} not found")
        sys.exit(1)
    
    xml_bytes = xml_path.read_bytes()
    org_code = input("Organization code: ")
    username = input("NEMSIS username: ")
    password = input("NEMSIS password (hidden): ")
    
    try:
        if dataset_type.upper() == "EMS":
            result = await submission_service.submit_ems_data(
                xml_bytes=xml_bytes,
                organization=org_code,
                username=username,
                password=password,
            )
        elif dataset_type.upper() == "DEM":
            result = await submission_service.submit_dem_data(
                xml_bytes=xml_bytes,
                organization=org_code,
                username=username,
                password=password,
            )
        else:
            print(f"Unknown dataset type: {dataset_type}")
            sys.exit(1)
        
        print(f"✓ Submission successful")
        print(f"  Request Handle: {result.request_handle}")
        print(f"  Status Code: {result.status_code}")
        print(f"  Message: {result.status_message}")
        
        if result.is_async:
            print(f"\n⏳ Async submission. Use handle for status checks.")
            
    except Exception as exc:
        print(f"✗ Submission failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", dest="xml_file", help="XML file to submit")
    parser.add_argument("--type", dest="type", default="EMS", help="Dataset type: EMS, DEM, State")
    args = parser.parse_args()
    
    if args.xml_file:
        asyncio.run(cli_submit_nemsis_data(args.xml_file, args.type))


# Note on credentials management:
# 
# In production, NEVER hardcode credentials. Instead:
# 
# 1. Store org-specific credentials in database
# 2. Use AWS Secrets Manager or similar for sensitive data
# 3. Retrieve credentials from org context (as shown in nemsis_routes.py)
# 4. Use environment variables for defaults only
# 
# Example org context:
#
#   class OrgContext(BaseModel):
#       organization_id: str
#       nemsis_username: str = Field(..., description="From secrets manager")
#       nemsis_password: str = Field(..., description="From secrets manager")
#
#   async def get_current_org_context() -> OrgContext:
#       # Get from request headers, JWT, or session
#       org_id = get_org_from_request()
#       return await db.orgs.get_nemsis_creds(org_id)
