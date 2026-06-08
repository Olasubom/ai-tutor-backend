import { apiClient } from './client';

export interface AppNotification {
  notification_id: string;
  type: 'mastery_drop' | 'task_due' | 'new_resource' | 'review_due' | 'streak_alert' | 'at_risk';
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
  action_url: string;
}

export async function getNotifications(learnerId: string) {
  const { data } = await apiClient.get<AppNotification[]>(`/notifications/${learnerId}`);
  return data;
}

export async function markNotificationRead(learnerId: string, notificationId: string) {
  await apiClient.post(`/notifications/${learnerId}/read/${notificationId}`);
}

export async function markAllNotificationsRead(learnerId: string) {
  const { data } = await apiClient.post<{ marked: number }>(`/notifications/${learnerId}/read-all`);
  return data;
}

export interface NotificationPreferences {
  study_reminders: boolean;
  new_recommendation_alerts: boolean;
  weekly_progress_email: boolean;
  task_due_alerts: boolean;
  mastery_drop_alerts: boolean;
}

const PREFS_KEY = 'aitutor_notification_prefs';

export async function getNotificationPreferences(learnerId: string): Promise<NotificationPreferences> {
  try {
    const { data } = await apiClient.get<NotificationPreferences>(`/notifications/preferences/${learnerId}`);
    return data;
  } catch {
    const raw = localStorage.getItem(`${PREFS_KEY}_${learnerId}`);
    if (raw) return JSON.parse(raw) as NotificationPreferences;
    return {
      study_reminders: true,
      new_recommendation_alerts: true,
      weekly_progress_email: false,
      task_due_alerts: true,
      mastery_drop_alerts: true,
    };
  }
}

export async function patchNotificationPreferences(
  learnerId: string,
  patch: Partial<NotificationPreferences>,
): Promise<NotificationPreferences> {
  try {
    const { data } = await apiClient.patch<NotificationPreferences>(`/notifications/preferences/${learnerId}`, patch);
    return data;
  } catch {
    // TODO: remove localStorage fallback when backend is always available
    const current = await getNotificationPreferences(learnerId);
    const merged = { ...current, ...patch };
    localStorage.setItem(`${PREFS_KEY}_${learnerId}`, JSON.stringify(merged));
    return merged;
  }
}
