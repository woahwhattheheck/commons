import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { measureRoads } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/roads")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const slack = new URL(request.url).searchParams.get("slack") || "";
        const roads = await measureRoads(slack);
        return Response.json({ roads }, { headers: corsHeaders() });
      },
    },
  },
});
