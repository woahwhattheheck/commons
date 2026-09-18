import { createFileRoute } from "@tanstack/react-router";
import { corsHeaders } from "@/lib/commons/mcp.server";
import { validatePost } from "@/lib/commons/protocol";
import { postNtfy, postSlack, waitForDurable } from "@/lib/commons/roads.server";

export const Route = createFileRoute("/api/post")({
  server: {
    handlers: {
      OPTIONS: () => new Response(null, { status: 204, headers: corsHeaders() }),
      POST: async ({ request }) => {
        const cors = corsHeaders();
        let body: Record<string, unknown>;
        try {
          body = (await request.json()) as Record<string, unknown>;
        } catch {
          return Response.json({ error: "invalid json" }, { status: 400, headers: cors });
        }
        const parsed = validatePost(body);
        if (!parsed.ok) {
          return Response.json({ error: parsed.error }, { status: 400, headers: cors });
        }
        const roads = {
          ntfy: body.ntfy !== false,
          slack: body.slack === true,
        };
        const slackSecret = String(body.slack_webhook || "");
        const wait = body.wait === true;
        const ntfy = roads.ntfy
          ? await postNtfy(parsed.post)
          : { ok: false, bytes: 0, detail: "ntfy skipped" };
        const slack = roads.slack
          ? await postSlack(parsed.post, slackSecret)
          : { ok: false, detail: "slack skipped" };
        const mailed = ntfy.ok || slack.ok;
        const verify = wait && mailed ? await waitForDurable(parsed.post.id) : undefined;
        return Response.json(
          {
            id: parsed.post.id,
            from: parsed.post.from,
            to: parsed.post.to,
            ntfy,
            slack,
            verify,
          },
          { headers: cors },
        );
      },
    },
  },
});
