import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { readPost } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/file")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const id = new URL(request.url).searchParams.get("id") || "";
        if (!id) {
          return Response.json({ error: "id required" }, { status: 400, headers: corsHeaders() });
        }
        const data = await readPost(id);
        return Response.json(data, { headers: corsHeaders() });
      },
    },
  },
});
