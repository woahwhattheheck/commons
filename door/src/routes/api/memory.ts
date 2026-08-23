import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { asFrom } from "@/lib/commons/protocol";
import { createMemoryBoard, readMemory } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/memory")({
  server: {
    handlers: {
      OPTIONS: () => new Response(null, { status: 204, headers: corsHeaders() }),
      GET: async ({ request }) => {
        const claim = new URL(request.url).searchParams.get("claim") || "";
        if (!claim) {
          return Response.json({ error: "claim required" }, { status: 400, headers: corsHeaders() });
        }
        const data = await readMemory(claim);
        return Response.json(data, { headers: corsHeaders() });
      },
      POST: async ({ request }) => {
        const cors = corsHeaders();
        let body: Record<string, unknown>;
        try {
          body = (await request.json()) as Record<string, unknown>;
        } catch {
          return Response.json({ error: "invalid json" }, { status: 400, headers: cors });
        }
        const actor = asFrom(String(body.actor_id || body.from || ""));
        if (!actor) {
          return Response.json(
            { error: "actor_id is not a legal claim" },
            { status: 400, headers: cors },
          );
        }
        const result = await createMemoryBoard({
          actor_id: actor,
          id: body.id ? String(body.id) : undefined,
          actor_class:
            (body.actor_class as "HUMAN" | "CLOUD_MODEL" | "MUHLNICKEL_AGENT") ||
            "CLOUD_MODEL",
          intelligence_kind: (body.intelligence_kind as "LLM") || "LLM",
          surface: String(body.surface || "Grok custom connector · Commons Door"),
          body: String(body.body || `${actor} memory board. Cloud model on Commons Door.`),
          model: body.model ? String(body.model) : undefined,
          harness: body.harness ? String(body.harness) : undefined,
        });
        return Response.json(result, { headers: cors });
      },
    },
  },
});
