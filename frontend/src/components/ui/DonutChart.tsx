import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';

interface DonutChartProps {
  value: number;
  total?: number;
  color?: string;
  height?: number;
}

export function DonutChart({ value, total = 100, color = '#006c4f', height = 160 }: DonutChartProps) {
  const data = [
    { name: 'value', value },
    { name: 'rest', value: Math.max(0, total - value) },
  ];
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} innerRadius={50} outerRadius={70} dataKey="value" startAngle={90} endAngle={-270}>
          <Cell fill={color} />
          <Cell fill="var(--color-border)" />
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
