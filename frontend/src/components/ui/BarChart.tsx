import { Bar, BarChart as ReBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface BarChartProps {
  data: Array<Record<string, string | number>>;
  dataKey: string;
  xKey?: string;
  color?: string;
  height?: number;
}

export function BarChart({ data, dataKey, xKey = 'name', color = '#0050cb', height = 200 }: BarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReBarChart data={data}>
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
        <YAxis hide />
        <Tooltip />
        <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
      </ReBarChart>
    </ResponsiveContainer>
  );
}
