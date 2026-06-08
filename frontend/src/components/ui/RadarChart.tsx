import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart as ReRadarChart,
  ResponsiveContainer,
} from 'recharts';

interface RadarChartProps {
  data: Array<{ subject: string; value: number }>;
  color?: string;
  height?: number;
}

export function RadarChart({ data, color = '#0050cb', height = 260 }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReRadarChart data={data}>
        <PolarGrid stroke="var(--color-border)" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} />
        <Radar dataKey="value" stroke={color} fill={color} fillOpacity={0.2} />
      </ReRadarChart>
    </ResponsiveContainer>
  );
}
