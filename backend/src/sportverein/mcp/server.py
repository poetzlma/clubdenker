"""FastMCP server instance for Klubdenker."""

from fastmcp import FastMCP

mcp = FastMCP("Klubdenker", instructions="KI-gestützter MCP-Server für Vereinsverwaltung")

# Import tool and resource registrations so they are executed at import time.
import sportverein.mcp.tools_mitglieder  # noqa: F401, E402
import sportverein.mcp.tools_beitraege  # noqa: F401, E402
import sportverein.mcp.tools_kommunikation  # noqa: F401, E402
import sportverein.mcp.tools_dashboard  # noqa: F401, E402
import sportverein.mcp.tools_setup  # noqa: F401, E402
import sportverein.mcp.tools_training  # noqa: F401, E402
import sportverein.mcp.tools_eingangsrechnung  # noqa: F401, E402
import sportverein.mcp.tools_audit  # noqa: F401, E402
import sportverein.mcp.resources  # noqa: F401, E402
