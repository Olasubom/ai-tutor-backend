import { Line, LineChart as ReLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface LineChartProps {
  data: Array<Record<string, string | number>>;
  dataKey: string;
  xKey?: string;
  color?: string;
  height?: number;
}

export function LineChart({ data, dataKey, xKey = 'name', color = '#0050cb', height = 80 }: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReLineChart data={data}>
        <XAxis dataKey={xKey} hide />
        <YAxis hide domain={['dataMin - 5', 'dataMax + 5']} />
        <Tooltip />
        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} />
      </ReLineChart>
    </ResponsiveContainer>
  );
}
