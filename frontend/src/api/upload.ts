import axios from 'axios';
import { apiClient, getApiBaseUrl } from './client';
import { useAuthStore } from '@/stores/authStore';

export interface UploadedMaterial {
  id: string;
  filename: string;
  original_name: string;
  file_type: string;
  file_size_mb: number;
  title: string;
  description?: string | null;
  course_id?: string | null;
  course_code?: string | null;
  course_title?: string | null;
  module_order?: number | null;
  uploaded_by: string;
  uploaded_by_name: string;
  college?: string | null;
  department?: string | null;
  status: 'pending_review' | 'approved' | 'rejected';
  created_at: string;
  url?: string | null;
  rejection_reason?: string | null;
}

export interface LecturerCourseOption {
  id: string;
  code: string;
  title: string;
  level: string;
  semester: string;
}

export interface UploadMaterialResponse {
  id: string;
  title: string;
  course_id: string;
  course_code: string;
  file_type: string;
  file_size_mb: number;
  status: string;
  message: string;
  url: string;
}

export async function getLecturerCourses(): Promise<LecturerCourseOption[]> {
  const { data } = await apiClient.get<LecturerCourseOption[]>('/lecturer/my-courses');
  return data;
}

export async function uploadMaterial(
  formData: FormData,
  onProgress?: (pct: number) => void,
): Promise<UploadMaterialResponse> {
  const { data } = await apiClient.post<UploadMaterialResponse>('/upload/material', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (!progressEvent.total) return;
      const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress?.(pct);
    },
  });
  return data;
}

export async function listMaterials(params?: {
  status?: string;
  department?: string;
  subject?: string;
  mine?: boolean;
}): Promise<{ materials: UploadedMaterial[]; total: number }> {
  const { data } = await apiClient.get<{ materials: UploadedMaterial[]; total: number }>(
    '/upload/materials',
    { params },
  );
  return data;
}

export async function approveMaterial(id: string): Promise<void> {
  await apiClient.patch(`/upload/material/${id}/approve`);
}

export async function rejectMaterial(id: string, reason?: string): Promise<void> {
  await apiClient.patch(`/upload/material/${id}/reject`, { reason });
}

export async function deleteMaterial(id: string): Promise<void> {
  await apiClient.delete(`/upload/material/${id}`);
}

export async function downloadMaterial(id: string, filename: string): Promise<void> {
  const { token } = useAuthStore.getState();
  const response = await axios.get(`${getApiBaseUrl()}/upload/material/${id}/download`, {
    responseType: 'blob',
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
      'X-API-Key': localStorage.getItem('aitutor_api_key') || import.meta.env.VITE_API_KEY || 'change_me',
    },
  });
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}

export function materialDownloadUrl(id: string): string {
  return `${getApiBaseUrl()}/upload/material/${id}/download`;
}

export async function openMaterialPreview(id: string): Promise<void> {
  const { token } = useAuthStore.getState();
  const response = await axios.get(materialDownloadUrl(id), {
    responseType: 'blob',
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
      'X-API-Key': localStorage.getItem('aitutor_api_key') || import.meta.env.VITE_API_KEY || 'change_me',
    },
  });
  const url = window.URL.createObjectURL(response.data);
  window.open(url, '_blank', 'noopener,noreferrer');
  setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
}

export function uploadIdFromContentItemId(contentItemId?: string): string | null {
  if (!contentItemId?.startsWith('upload_')) return null;
  return contentItemId.replace(/^upload_/, '');
}
