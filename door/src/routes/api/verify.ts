import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { verifyDurability } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/verify")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const url = new URL(request.url);
        const id = url.searchParams.get("id") || "";
        if (!id) {
          return Response.json({ error: "id required" }, { status: 400, headers: corsHeaders() });
        }
        const sha = url.searchParams.get("sha") || undefined;
        const result = await verifyDurability(id, sha);
        return Response.json(result, { headers: corsHeaders() });
      },
    },
  },
});
