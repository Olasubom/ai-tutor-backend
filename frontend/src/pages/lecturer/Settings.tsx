import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/useAuth';
import { fetchDepartments, fetchFaculties } from '@/api/courses';

export default function LecturerSettings() {
  const { user } = useAuth();
  const faculty = fetchFaculties().find((f) => f.id === user?.faculty_id);
  const department = fetchDepartments().find((d) => d.id === user?.department_id);

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-[28px] font-extrabold">Profile</h1>
      <Card className="space-y-4 p-6">
        {[
          ['Name', user?.name],
          ['Email', user?.email],
          ['Staff ID', user?.staff_id],
          ['Faculty', faculty?.name],
          ['Department', department?.name],
          ['Status', user?.status === 'active' ? 'Active' : user?.status],
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
