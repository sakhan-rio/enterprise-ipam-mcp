import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from ipam_mcp.middleware.authorization import EntraRoleAuthorizationMiddleware
from ipam_mcp.middleware.audit import AuditMiddleware
from ipam_mcp.telemetry import configure_telemetry
from ipam_mcp.tools.read import register_read_tools
from ipam_mcp.tools.write import register_write_tools

load_dotenv(override=False)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
configure_telemetry()

mcp = FastMCP("Enterprise IPAM MCP Server")
mcp.add_middleware(ErrorHandlingMiddleware(include_traceback=(log_level == "DEBUG"), transform_errors=True))
mcp.add_middleware(EntraRoleAuthorizationMiddleware())
mcp.add_middleware(AuditMiddleware())
register_read_tools(mcp)
register_write_tools(mcp)

http_app = mcp.http_app(transport="sse") if os.getenv("MCP_TRANSPORT") == "sse" else mcp.http_app()
app = FastAPI(lifespan=http_app.lifespan)
app.mount("/ipam", http_app)

@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok"})
