from fastapi import FastAPI
from fastmcp import FastMCP
from typing import Dict, Any
import os
import pandas as pd

# Import your agents
from agents.concerns_agent import BH_concern_agent
from agents.free_benefits import create_benefits_agent
from agents.initial_call_routing import call_routing_agent
from agents.pcp_appointment import pcp_appointment_flow
from agents.SDoH import SDoH_Agent
from agents.validation_agent import create_validation_agent

# Initialize FastMCP server
mcp = FastMCP(name="Outbound Agents MCP Server")

# Generate the FastMCP ASGI application
mcp_app = mcp.http_app(path='/agents')

# Define MCP tools
@mcp.tool
async def validation_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validates patient information against records"""
    try:
        full_name = payload.get("full_name")
        dob = payload.get("dob")
        if not full_name or not dob:
            return {"valid": False, "message": "Both full_name and dob are required"}
        return validate_patient(full_name, dob)
    except Exception as e:
        return {"valid": False, "message": f"Error during validation: {str(e)}"}

@mcp.tool
async def concerns_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles patient behavioral health concerns"""
    if user_response := payload.get("user_response"):
        os.environ["MOCK_USER_INPUT"] = user_response
    return {"result": BH_concern_agent()}

@mcp.tool
async def benefits_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles benefits related queries"""
    if user_response := payload.get("user_response"):
        os.environ["MOCK_USER_INPUT"] = user_response
    return {"result": create_benefits_agent()}

@mcp.tool
async def routing_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles initial call routing"""
    if user_response := payload.get("user_response"):
        os.environ["MOCK_USER_INPUT"] = user_response
    return {"result": call_routing_agent()}

@mcp.tool
async def pcp_appointment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles PCP appointment scheduling"""
    if user_response := payload.get("user_response"):
        os.environ["MOCK_USER_INPUT"] = user_response
    return {"result": pcp_appointment_flow()}

@mcp.tool
async def sdoh_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handles Social Determinants of Health assessment"""
    if user_response := payload.get("user_response"):
        os.environ["MOCK_USER_INPUT"] = user_response
    return {"result": SDoH_Agent()}

def validate_patient(full_name: str, dob: str) -> Dict[str, Any]:
    """Validate patient details against the CSV file"""
    try:
        # Read the CSV file
        df = pd.read_csv('input/DummyPatientListPOC.csv', dtype=str)
        
        # Clean the data
        df = df.fillna('')
        df['Full Name'] = df['Full Name'].str.strip()
        df['DOB'] = df['DOB'].str.strip()
        full_name = str(full_name).strip()
        dob = str(dob).strip()
        
        # Find exact matches
        exact_matches = df[
            (df['Full Name'] == full_name) & 
            (df['DOB'] == dob)
        ]
        
        if not exact_matches.empty:
            first_match = exact_matches.iloc[0]
            return {
                "valid": True,
                "message": "Patient validated successfully",
                "patient_info": {
                    "member_id": first_match['Member ID'],
                    "full_name": first_match['Full Name'],
                    "dob": first_match['DOB'],
                    "phone": first_match['Phone Number'],
                    "pcp_name": first_match['PCP Name'],
                    "pcp_appointment": "Not scheduled" if pd.isna(first_match['PCP Appointment Date']) else first_match['PCP Appointment Date']
                }
            }
        return {"valid": False, "message": "Patient not found in records"}
    except Exception as e:
        return {"valid": False, "message": f"Error during validation: {str(e)}"}


# Create FastAPI app and mount the MCP Streamable HTTP application
app = FastAPI(
    title="Outbound Agents MCP Server",
    description="Model Context Protocol server exposing outbound agents as tools",
    version="1.0.0",
    lifespan=mcp_app.lifespan
)

# Mount the MCP application
app = FastAPI(title="FastMCP with Uvicorn", lifespan=mcp_app.lifespan)
app.mount("/mcp",mcp_app)

#app.mount("/mcp", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
