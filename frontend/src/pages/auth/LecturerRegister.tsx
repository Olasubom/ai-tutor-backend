import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { AuthSidePanel } from '@/components/auth/AuthSidePanel';
import { registerLecturer } from '@/api/auth';
import { fetchColleges, fetchDepartments } from '@/api/courses';
import { useToastStore } from '@/components/ui/Toast';
import axios from 'axios';

const schema = z
  .object({
    name: z.string().min(2, 'Name is required'),
    email: z.string().email(),
    nuc_staff_id: z.string().min(3, 'Staff ID is required'),
    college: z.string().min(1, 'Select a college'),
    department: z.string().min(1, 'Select a department'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, { message: 'Passwords must match', path: ['confirm'] });

type FormData = z.infer<typeof schema>;

export default function LecturerRegister() {
  const toast = useToastStore((s) => s.add);
  const [collegeId, setCollegeId] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [nucError, setNucError] = useState('');

  const { data: colleges = [] } = useQuery({ queryKey: ['colleges'], queryFn: fetchColleges });
  const activeCollegeId = collegeId || colleges[0]?.id || '';
  const { data: departments = [] } = useQuery({
    queryKey: ['departments', activeCollegeId],
    queryFn: () => fetchDepartments(activeCollegeId),
    enabled: !!activeCollegeId,
  });

  const filteredDepartments = departments.filter(
    (d) => d.college_id === activeCollegeId || d.faculty_id === activeCollegeId,
  );

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      college: colleges[0]?.id ?? '',
      department: filteredDepartments[0]?.id ?? '',
    },
  });

  const selectedCollegeId = watch('college') || activeCollegeId;
  const selectedCollege = colleges.find((c) => c.id === selectedCollegeId);

  const onSubmit = async (data: FormData) => {
    setNucError('');
    try {
      const dept = filteredDepartments.find((d) => d.id === data.department);
      await registerLecturer({
        name: data.name,
        email: data.email,
        password: data.password,
        nuc_staff_id: data.nuc_staff_id,
        college: selectedCollege?.name ?? '',
        department: dept?.name ?? '',
      });
      setSubmitted(true);
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 400) {
        const detail = e.response.data?.detail;
        if (typeof detail === 'string' && detail.toLowerCase().includes('staff id')) {
          setNucError(detail);
          return;
        }
      }
      toast(e instanceof Error ? e.message : 'Registration failed', 'error');
    }
  };

  if (submitted) {
    return (
      <div className="grid min-h-screen lg:grid-cols-2">
        <div className="flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-md text-center">
            <h1 className="text-[28px] font-extrabold">Request submitted</h1>
            <p className="mt-4 text-text-secondary">
              Account request submitted. An administrator will review and approve your account. You will be able to log
              in once approved.
            </p>
            <Link to="/login" className="mt-8 inline-block font-semibold text-primary">
              Return to Sign In
            </Link>
          </div>
        </div>
        <AuthSidePanel panel="lecturer_register" />
      </div>
    );
  }

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
            <div>
              <Input
                label="NUC / Staff ID"
                placeholder="e.g. NUC-2024-001"
                error={nucError || errors.nuc_staff_id?.message}
                {...register('nuc_staff_id')}
              />
              <p className="mt-1 text-[12px] text-text-muted">
                Your NUC-issued staff identification number. Required for account verification.
              </p>
            </div>

            <Select
              label="College"
              error={errors.college?.message}
              options={colleges.map((c) => ({ value: c.id, label: c.name }))}
              {...register('college', {
                onChange: (e) => {
                  const id = e.target.value;
                  setCollegeId(id);
                  setValue('college', id);
                  const firstDept = departments.find((d) => d.college_id === id || d.faculty_id === id);
                  setValue('department', firstDept?.id ?? '');
                },
              })}
            />

            <Select
              label="Department"
              error={errors.department?.message}
              options={
                filteredDepartments.length
                  ? filteredDepartments.map((d) => ({ value: d.id, label: d.name }))
                  : [{ value: '', label: 'No departments in this college' }]
              }
              {...register('department')}
            />

            <Input label="Password" type="password" error={errors.password?.message} {...register('password')} />
            <Input label="Confirm Password" type="password" error={errors.confirm?.message} {...register('confirm')} />

            <Button type="submit" fullWidth disabled={isSubmitting}>
              {isSubmitting ? 'Submitting…' : 'Submit for Approval'}
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
