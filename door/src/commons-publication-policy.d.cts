declare const policy: {
  POLICY_CONTEXT: string;
  checkPublication(body: string, subject?: string): {allowed: boolean; code: string; message: string; rule: string | null};
  requirePublication(body: string, subject?: string): unknown;
};
export = policy;
