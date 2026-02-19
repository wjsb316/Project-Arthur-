import type { PipelineTiming } from '../types';

interface Props {
  timing: PipelineTiming | null;
  dark?: boolean;
}

function fmt(s: number | null): string {
  if (s === null || s === undefined) return '  —  ';
  return s.toFixed(3).padStart(7, '0') + 's';
}

export default function PipelineTimingDisplay({ timing, dark = false }: Props) {
  const t = timing ?? { t1_s: null, t2_s: null, t3_s: null, t4_s: null };

  const bg = dark ? 'rgba(0,0,0,0.45)' : 'rgba(248,250,252,0.92)';
  const border = dark ? '1px solid rgba(255,255,255,0.12)' : '1px solid rgba(0,0,0,0.08)';
  const labelColor = dark ? 'rgba(255,255,255,0.5)' : '#94a3b8';
  const valueColor = dark ? 'rgba(255,255,255,0.9)' : '#334155';

  const rows: { label: string; value: number | null }[] = [
    { label: 'memory',    value: t.t1_s },
    { label: 'llm',       value: t.t2_s },
    { label: 'voice₁',   value: t.t3_s },
    { label: 'voice∞', value: t.t4_s },
  ];

  return (
    <div
      style={{
        background: bg,
        border,
        borderRadius: '6px',
        padding: '0.3rem 0.6rem',
        backdropFilter: 'blur(8px)',
        display: 'inline-flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: '0.75rem',
      }}
    >
      {rows.map(({ label, value }) => (
        <div
          key={label}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: '1rem',
            lineHeight: '1.3',
            whiteSpace: 'pre',
          }}
        >
          <span style={{ color: labelColor }}>{label.trim()}</span>
          <span style={{ color: valueColor }}>{fmt(value)}</span>
        </div>
      ))}
    </div>
  );
}
