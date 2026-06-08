import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { AuthSidePanel } from '@/components/auth/AuthSidePanel';
import { registerLecturer } from '@/api/auth';
import { fetchDepartments, fetchFaculties } from '@/api/courses';
import { useToastStore } from '@/components/ui/Toast';

const schema = z
  .object({
    name: z.string().min(2, 'Name is required'),
    email: z.string().email(),
    staff_id: z.string().min(3, 'Staff ID is required'),
    faculty_id: z.string().min(1, 'Select a faculty'),
    department_id: z.string().min(1, 'Select a department'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, { message: 'Passwords must match', path: ['confirm'] });

type FormData = z.infer<typeof schema>;

export default function LecturerRegister() {
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);
  const { data: faculties = [] } = useQuery({ queryKey: ['faculties'], queryFn: fetchFaculties });
  const { data: departments = [] } = useQuery({ queryKey: ['departments'], queryFn: fetchDepartments });
  const [facultyId, setFacultyId] = useState('');
  const activeFacultyId = facultyId || faculties[0]?.id || '';

  const filteredDepartments = departments.filter((d) => d.faculty_id === activeFacultyId);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      faculty_id: faculties[0]?.id ?? '',
      department_id: filteredDepartments[0]?.id ?? '',
    },
  });

  const onSubmit = async (data: FormData) => {
    try {
      await registerLecturer({
        name: data.name,
        email: data.email,
        staff_id: data.staff_id,
        faculty_id: data.faculty_id,
        department_id: data.department_id,
        password: data.password,
      });
      navigate('/register/lecturer/pending', { state: { email: data.email } });
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Registration failed', 'error');
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <h1 className="text-[28px] font-extrabold tracking-tight">Create your lecturer account</h1>
          <p className="mt-2 text-text-secondary">
            Register with your university staff ID. An administrator will verify your account before you can sign in.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4">
            <Input label="Full Name" error={errors.name?.message} {...register('name')} />
            <Input label="Email address" type="email" error={errors.email?.message} {...register('email')} />
            <Input
              label="Staff ID (NUC)"
              placeholder="e.g. NUC-2024-001"
              error={errors.staff_id?.message}
              {...register('staff_id')}
            />
            <p className="-mt-2 text-[12px] text-text-muted">
              Your ID must be pre-approved by your department administrator.
            </p>

            <Select
              label="Faculty"
              error={errors.faculty_id?.message}
              options={faculties.map((f) => ({ value: f.id, label: f.name }))}
              {...register('faculty_id', {
                onChange: (e) => {
                  const id = e.target.value;
                  setFacultyId(id);
                  setValue('faculty_id', id);
                  const firstDept = departments.find((d) => d.faculty_id === id);
                  setValue('department_id', firstDept?.id ?? '');
                },
              })}
            />

            <Select
              label="Department"
              error={errors.department_id?.message}
              options={
                filteredDepartments.length
                  ? filteredDepartments.map((d) => ({ value: d.id, label: d.name }))
                  : [{ value: '', label: 'No departments in this faculty' }]
              }
              {...register('department_id')}
            />

            <Input label="Password" type="password" error={errors.password?.message} {...register('password')} />
            <Input
              label="Confirm Password"
              type="password"
              error={errors.confirm?.message}
              {...register('confirm')}
            />

            <Button type="submit" fullWidth disabled={isSubmitting}>
              Submit for Approval
            </Button>
          </form>

          <p className="mt-4 text-center text-[14px] text-text-muted">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      <AuthSidePanel panel="lecturer_register" />
    </div>
  );
}
