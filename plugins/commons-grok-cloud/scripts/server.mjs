#!/usr/bin/env node

import { createHash } from "node:crypto";
import process from "node:process";

const VERSION = "1.0.0";
const COMMONS_MCP = "https://commons-spark-mcp.vercel.app/mcp";
const SLACK_CHANNEL = "C0BRGMDQB6G";
const ID_RE = /^[A-Za-z0-9._-]{8,80}$/;
const GROK_URL_RE = /^https:\/\/grok\.com\/c\/[A-Za-z0-9_-]+(?:[/?#].*)?$/;

const ROUTES = Object.freeze({
  "grokcom-revenue": {
    executor: "chatgpt-cloud-browser",
    surface: "https://grok.com/",
    orchestrator_tool: "route_grokcom_revenue_work",
    durable_job_path: "wake_jobs/<task-id>.json",
    task_sources: ["slack", "commons-mcp", "action-ops", "user"],
    receipt: "grok.com/c/... URL plus exact prompt and result",
  },
  "gemini-spark": {
    executor: "gemini-spark",
    surface: COMMONS_MCP,
    carrier: "carriers/gemini-spark.json",
  },
  commons: { executor: "streamable-http-mcp", surface: COMMONS_MCP },
  slack: { executor: "chatgpt-slack-connector", channel: SLACK_CHANNEL },
  github: { executor: "chatgpt-github-connector", repository: "woahwhattheheck/commons" },
});

const AUTOMATION_PROMPT = [
  "Read new GROK TASK messages in Slack #commons (C0BRGMDQB6G).",
  "Send every event to Commons MCP route_grokcom_revenue_work at INTAKE.",
  "Skip completed or live-owned dedupe keys; execute only SEND_TO_GROKCOM packets.",
  "Use the commons-grok-cloud skill and the account's cloud browser to run the exact returned prompt once.",
  "Build the real grok.com artifact, feed it to GROKCOM_RESULT, and reply in the originating Slack thread and Commons.",
].join(" ");

function assertId(value) {
  const id = String(value ?? "").trim();
  if (!ID_RE.test(id)) throw new Error("task_id must be 8-80 Commons ID characters");
  return id;
}

function receiptId(taskId, suffix) {
  const id = assertId(taskId);
  const tail = `-grok-${suffix}`;
  if (id.length + tail.length <= 80) return id + tail;
  const digest = createHash("sha256").update(id).digest("hex").slice(0, 10);
  return `${id.slice(0, 80 - tail.length - 11)}-${digest}${tail}`;
}

function list(value) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

export function buildArtifact(args = {}) {
  const taskId = assertId(args.task_id);
  const conversationUrl = String(args.conversation_url ?? "").trim();
  if (!GROK_URL_RE.test(conversationUrl)) {
    throw new Error("conversation_url must be an actual https://grok.com/c/... URL");
  }
  const exactPrompt = String(args.exact_prompt ?? "");
  const result = String(args.result ?? "");
  const inspectedSha = String(args.inspected_sha ?? "").trim();
  if (!exactPrompt.trim() || !result.trim()) throw new Error("exact_prompt and result are required");
  if (!/^[0-9a-f]{7,40}$/i.test(inspectedSha)) throw new Error("inspected_sha must be a Git SHA");
  const state = String(args.state ?? "READY_FOR_INTEGRATION").trim();
  const event = args.event && typeof args.event === "object" && !Array.isArray(args.event) ? args.event : {};
  if (!Object.keys(event).length) throw new Error("original Slack event is needed to preserve the orchestrator task hash");
  const changedPaths = list(args.changed_paths);
  const checks = list(args.checks);
  const lines = [
    `GROK RESULT — ${taskId}`,
    `state: ${state}`,
    `conversation: ${conversationUrl}`,
    `inspected_sha: ${inspectedSha}`,
    args.model ? `model: ${String(args.model)}` : "",
    args.account ? `account: ${String(args.account)}` : "",
    args.usage ? `usage: ${String(args.usage)}` : "",
    changedPaths.length ? `changed_paths: ${changedPaths.join(", ")}` : "changed_paths: none",
    checks.length ? `checks: ${checks.join("; ")}` : "checks: not reported",
    "exact_prompt:",
    exactPrompt,
    "lossless_result:",
    result,
  ].filter(Boolean);
  const receiptBody = lines.join("\n");
  const artifact = {
    task_id: taskId,
    conversation_url: conversationUrl,
    exact_prompt: exactPrompt,
    lossless_result: result,
    inspected_sha: inspectedSha,
    model: args.model ? String(args.model) : "",
    account: args.account ? String(args.account) : "",
    usage: args.usage ? String(args.usage) : "",
    changed_paths: changedPaths,
    checks,
    state,
  };
  return {
    state,
    task_id: taskId,
    conversation_url: conversationUrl,
    artifact,
    orchestrator_tool: "route_grokcom_revenue_work",
    orchestrator_arguments: { stage: "GROKCOM_RESULT", event, artifact },
    commons_post: {
      id: receiptId(taskId, "result"),
      to: "TOOLS",
      board: "TOOLS",
      subject: "grok.com cloud execution",
      body: receiptBody,
    },
  };
}

export function classifyPreflight(args = {}) {
  if (!args.browser_bridge) return { state: "BROWSER_UNAVAILABLE", retry_same_session: false };
  if (!args.page_backend) return { state: "PAGE_BACKEND_UNAVAILABLE", retry_same_session: false };
  if (String(args.grok_page ?? "") === "login") return { state: "PROVIDER_SIGN_IN", retry_same_session: false };
  const url = String(args.conversation_url ?? "").trim();
  if (String(args.grok_page ?? "") !== "ready" || (url && !GROK_URL_RE.test(url))) {
    return { state: "PAGE_UNCONFIRMED", retry_same_session: false };
  }
  return { state: "READY", retry_same_session: true };
}

export function getBridge() {
  return {
    schema: "commons-grok-cloud-v1",
    commons_mcp: COMMONS_MCP,
    slack_channel: SLACK_CHANNEL,
    routes: ROUTES,
    automation_prompt: AUTOMATION_PROMPT,
    receipt_fields: [
      "task_id", "event", "conversation_url", "exact_prompt", "result", "inspected_sha",
      "model", "account", "usage", "changed_paths", "checks", "state",
    ],
    failure_states: ["BROWSER_UNAVAILABLE", "PAGE_BACKEND_UNAVAILABLE", "PROVIDER_SIGN_IN", "PAGE_UNCONFIRMED"],
  };
}

const TOOLS = [
  {
    name: "get_cloud_bridge",
    description: "Return the one-install Grok/Commons/Slack/Gemini cloud route and automation prompt.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "build_grok_artifact",
    description: "Turn a real cloud-browser Grok result into the canonical orchestrator artifact and Commons receipt.",
    inputSchema: {
      type: "object",
      required: ["task_id", "event", "conversation_url", "exact_prompt", "result", "inspected_sha"],
      properties: {
        task_id: { type: "string" }, event: { type: "object", additionalProperties: true },
        conversation_url: { type: "string" }, exact_prompt: { type: "string" },
        result: { type: "string" }, inspected_sha: { type: "string" }, model: { type: "string" },
        account: { type: "string" }, usage: { type: "string" }, state: { type: "string" },
        changed_paths: { type: "array", items: { type: "string" } }, checks: { type: "array", items: { type: "string" } },
      },
      additionalProperties: false,
    },
  },
  {
    name: "classify_grok_preflight",
    description: "Classify measured cloud browser and grok.com page readiness without repeated blind attempts.",
    inputSchema: {
      type: "object",
      properties: {
        browser_bridge: { type: "boolean" }, page_backend: { type: "boolean" }, grok_page: { type: "string" },
        conversation_url: { type: "string" },
      },
      additionalProperties: false,
    },
  },
];

function toolResult(payload) {
  return { content: [{ type: "text", text: JSON.stringify(payload, null, 2) }], structuredContent: payload };
}

function callTool(name, args) {
  if (name === "get_cloud_bridge") return getBridge();
  if (name === "build_grok_artifact") return buildArtifact(args);
  if (name === "classify_grok_preflight") return classifyPreflight(args);
  throw new Error(`unknown tool: ${name}`);
}

function handle(message) {
  const id = message?.id;
  if (message?.method === "initialize") {
    return { jsonrpc: "2.0", id, result: { protocolVersion: "2025-03-26", capabilities: { tools: {} }, serverInfo: { name: "commons-grok-cloud", version: VERSION } } };
  }
  if (message?.method === "tools/list") return { jsonrpc: "2.0", id, result: { tools: TOOLS } };
  if (message?.method === "tools/call") {
    try { return { jsonrpc: "2.0", id, result: toolResult(callTool(message.params?.name, message.params?.arguments ?? {})) }; }
    catch (error) { return { jsonrpc: "2.0", id, result: { isError: true, content: [{ type: "text", text: String(error.message || error) }] } }; }
  }
  if (message?.method === "ping") return { jsonrpc: "2.0", id, result: {} };
  if (id === undefined) return null;
  return { jsonrpc: "2.0", id, error: { code: -32601, message: "method not found" } };
}

function selfTest() {
  const result = buildArtifact({ task_id: "cloud-grok-test-20260828-01", event: { event_id: "Ev1", channel: SLACK_CHANNEL, message_ts: "1", text: "task" }, conversation_url: "https://grok.com/c/abc_123", exact_prompt: "p", result: "r", inspected_sha: "d778772" });
  if (result.state !== "READY_FOR_INTEGRATION" || result.orchestrator_arguments.stage !== "GROKCOM_RESULT") throw new Error("artifact fixture failed");
  if (classifyPreflight({}).state !== "BROWSER_UNAVAILABLE") throw new Error("browser fixture failed");
  if (classifyPreflight({ browser_bridge: true }).state !== "PAGE_BACKEND_UNAVAILABLE") throw new Error("backend fixture failed");
  if (classifyPreflight({ browser_bridge: true, page_backend: true, grok_page: "login" }).state !== "PROVIDER_SIGN_IN") throw new Error("sign-in fixture failed");
  if (classifyPreflight({ browser_bridge: true, page_backend: true, grok_page: "ready", conversation_url: "https://grok.com/c/abc" }).state !== "READY") throw new Error("ready fixture failed");
  if (!getBridge().automation_prompt.includes("GROK TASK")) throw new Error("automation fixture failed");
  if (new Set(getBridge().receipt_fields).size !== getBridge().receipt_fields.length) throw new Error("duplicate receipt field");
  process.stdout.write("commons-grok-cloud self-test: PASS\n");
}

function runStdio() {
  let buffer = Buffer.alloc(0);
  process.stdin.on("data", (chunk) => { buffer = Buffer.concat([buffer, chunk]); drain(); });
  process.stdin.resume();

  function send(payload, mode) {
    if (!payload) return;
    const body = JSON.stringify(payload);
    if (mode === "content-length") process.stdout.write(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
    else process.stdout.write(body + "\n");
  }

  function drain() {
    while (buffer.length) {
      const text = buffer.toString("utf8");
      if (text.startsWith("Content-Length:")) {
        const headerEnd = text.indexOf("\r\n\r\n");
        if (headerEnd < 0) return;
        const match = /^Content-Length:\s*(\d+)/i.exec(text.slice(0, headerEnd));
        if (!match) throw new Error("invalid Content-Length frame");
        const headerBytes = Buffer.byteLength(text.slice(0, headerEnd + 4));
        const length = Number(match[1]);
        if (buffer.length < headerBytes + length) return;
        const body = buffer.subarray(headerBytes, headerBytes + length).toString("utf8");
        buffer = buffer.subarray(headerBytes + length);
        try { send(handle(JSON.parse(body)), "content-length"); }
        catch (error) { send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: String(error.message || error) } }, "content-length"); }
      } else {
        const newline = buffer.indexOf(10);
        if (newline < 0) return;
        const body = buffer.subarray(0, newline).toString("utf8").trim();
        buffer = buffer.subarray(newline + 1);
        if (!body) continue;
        try { send(handle(JSON.parse(body)), "jsonl"); }
        catch (error) { send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: String(error.message || error) } }, "jsonl"); }
      }
    }
  }
}

if (process.argv.includes("--self-test")) selfTest();
else if (process.argv.includes("--stdio")) runStdio();
else process.stdout.write(JSON.stringify(getBridge(), null, 2) + "\n");
