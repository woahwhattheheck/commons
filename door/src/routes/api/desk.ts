import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { readDesk } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/desk")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const limit = Number(new URL(request.url).searchParams.get("limit") || 80);
        const data = await readDesk(Math.min(120, Math.max(1, limit)));
        return Response.json(data, { headers: corsHeaders() });
      },
    },
  },
});
