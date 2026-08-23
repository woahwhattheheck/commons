import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { readPulse } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/pulse")({
  server: {
    handlers: {
      GET: async () => {
        const pulse = await readPulse();
        return Response.json({ pulse }, { headers: corsHeaders() });
      },
    },
  },
});
