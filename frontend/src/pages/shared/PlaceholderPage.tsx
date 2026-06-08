import { Card } from '@/components/ui/Card';

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <Card>
      <h1 className="text-[28px] font-extrabold">{title}</h1>
      <p className="mt-2 text-text-secondary">This section is scaffolded and ready for full implementation.</p>
    </Card>
  );
}
