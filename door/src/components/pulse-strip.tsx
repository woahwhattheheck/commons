export function PulseStrip(props: {
  pulse: {
    seq: number;
    head: string;
    ts: string;
    post_count: number;
    newest?: string[];
    instruction?: string;
  } | null;
}) {
  const { pulse } = props;

  if (!pulse) {
    return (
      <p className="min-w-0 overflow-x-hidden break-words font-mono text-xs leading-relaxed text-subtle">
        No pulse. Bake may be down.
      </p>
    );
  }

  const bits = [
    `pulse ${pulse.seq}`,
    `${pulse.post_count} posts`,
    pulse.head.slice(0, 8),
    pulse.ts,
  ];
  if (pulse.instruction) bits.push(pulse.instruction);

  return (
    <p className="min-w-0 overflow-x-hidden whitespace-normal break-words font-mono text-xs leading-relaxed text-subtle">
      {bits.join(" · ")}
    </p>
  );
}
