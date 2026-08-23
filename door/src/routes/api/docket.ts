import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { readDocket } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/docket")({
  server: {
    handlers: {
      GET: async () => {
        const data = await readDocket();
        return Response.json(data, { headers: corsHeaders() });
      },
    },
  },
});
