import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { isLedgerKind, readLedger } from "@/lib/commons/ledgers.server";

export const Route = createFileRoute("/api/ledgers")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const kind = new URL(request.url).searchParams.get("kind") || "";
        if (!isLedgerKind(kind)) {
          return Response.json(
            { error: "kind required: failed|claims|tools|wake" },
            { status: 400, headers: corsHeaders() },
          );
        }
        const data = await readLedger(kind);
        return Response.json(data, { headers: corsHeaders() });
      },
    },
  },
});
