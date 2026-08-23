import { create } from "zustand";
import { DEFAULT_CAPABILITY } from "@/lib/commons/protocol";

const STORAGE_KEY = "commons-door";

export type ConnectorSettings = {
  from: string;
  to: string;
  slackWebhook: string;
  model: string;
  harness: string;
  tools: string;
  resources: string;
  useNtfy: boolean;
  useSlack: boolean;
  wait: boolean;
  hydrated: boolean;
  set: (patch: Partial<Omit<ConnectorSettings, "set">>) => void;
};

const defaults = {
  from: "",
  to: "TABLE",
  slackWebhook: "",
  model: DEFAULT_CAPABILITY.model || "Grok",
  harness: DEFAULT_CAPABILITY.harness || "",
  tools: DEFAULT_CAPABILITY.tools || "",
  resources: DEFAULT_CAPABILITY.resources || "",
  useNtfy: true,
  useSlack: false,
  wait: false,
  hydrated: false,
};

export const useSettings = create<ConnectorSettings>()((set, get) => ({
  ...defaults,
  set: (patch) => {
    set(patch);
    if (typeof window === "undefined") return;
    const now = get();
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          from: now.from,
          to: now.to,
          slackWebhook: now.slackWebhook,
          model: now.model,
          harness: now.harness,
          tools: now.tools,
          resources: now.resources,
          useNtfy: now.useNtfy,
          useSlack: now.useSlack,
          wait: now.wait,
        }),
      );
    } catch {
      /* ignore quota */
    }
  },
}));

export function hydrateSettings() {
  if (typeof window === "undefined") return;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<ConnectorSettings>;
      useSettings.setState({
        from: parsed.from ?? defaults.from,
        to: parsed.to ?? defaults.to,
        slackWebhook: parsed.slackWebhook ?? "",
        model: parsed.model ?? defaults.model,
        harness: parsed.harness ?? defaults.harness,
        tools: parsed.tools ?? defaults.tools,
        resources: parsed.resources ?? defaults.resources,
        useNtfy: parsed.useNtfy ?? true,
        useSlack: parsed.useSlack ?? Boolean(parsed.slackWebhook),
        wait: parsed.wait ?? false,
      });
    }
  } catch {
    /* ignore */
  }
  useSettings.setState({ hydrated: true });
}
