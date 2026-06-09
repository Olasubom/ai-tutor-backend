import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/useAuth';
import { getMe } from '@/api/auth';

export default function LecturerSettings() {
  const { user } = useAuth();
  const { data: profile } = useQuery({ queryKey: ['lecturer-me'], queryFn: getMe, enabled: !!user });

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-[28px] font-extrabold">Profile</h1>
      <Card className="space-y-4 p-6">
        {[
          ['Name', profile?.name ?? user?.name],
          ['Email', profile?.email ?? user?.email],
          ['Staff ID', profile?.nuc_staff_id],
          ['College', profile?.college],
          ['Department', profile?.department],
          ['Status', profile?.is_verified ? 'Active' : 'Pending verification'],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between border-b border-border pb-3 text-[14px] last:border-0">
            <span className="text-text-muted">{label}</span>
            <span className="font-medium text-text-primary">{value ?? '—'}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}
