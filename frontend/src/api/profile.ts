import { patchProfile as patchAuthProfile } from './auth';

/** @deprecated use patchAuthProfile from auth.ts */
export async function patchProfile(body: {
  learner_id?: string;
  full_name?: string;
  institution?: string;
  department_id?: string;
  academic_level?: string;
  name?: string;
  department?: string;
  college?: string;
}) {
  const patch: Record<string, string> = {};
  const name = body.full_name ?? body.name;
  if (name) patch.name = name;
  if (body.department) patch.department = body.department;
  if (body.institution) patch.institution = body.institution;
  if (body.academic_level) patch.academic_level = body.academic_level;
  if (body.college) patch.college = body.college;
  return patchAuthProfile(patch);
}
