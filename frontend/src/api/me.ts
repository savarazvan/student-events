import { request, requestBlob } from './client';
import type {
  MyRegistrationResponse,
  MyTask,
  NotificationItem,
  NotificationListResponse,
  TicketResponse,
} from '../types';

export function getMyRegistrations(
  upcoming?: boolean,
  includeCancelled?: boolean,
): Promise<MyRegistrationResponse[]> {
  const params = new URLSearchParams();
  if (upcoming) params.set('upcoming', 'true');
  if (includeCancelled) params.set('include_cancelled', 'true');
  const qs = params.toString();
  return request<MyRegistrationResponse[]>(
    'GET',
    `/me/registrations${qs ? `?${qs}` : ''}`,
  );
}

export function getTicket(ticketId: string): Promise<TicketResponse> {
  return request<TicketResponse>('GET', `/me/tickets/${ticketId}`);
}

export function getTicketQrSvg(ticketId: string): Promise<Blob> {
  return requestBlob('GET', `/me/tickets/${ticketId}/qr.svg`);
}

export function getNotifications(
  unreadOnly = false,
  limit = 30,
): Promise<NotificationListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (unreadOnly) params.set('unread_only', 'true');
  return request<NotificationListResponse>('GET', `/me/notifications?${params.toString()}`);
}

export function markNotificationRead(id: string): Promise<NotificationItem> {
  return request<NotificationItem>('POST', `/me/notifications/${id}/read`);
}

export function markAllNotificationsRead(): Promise<{ updated: number }> {
  return request<{ updated: number }>('POST', '/me/notifications/read-all');
}

export function getMyTasks(includeDone = false): Promise<MyTask[]> {
  return request<MyTask[]>('GET', `/me/tasks${includeDone ? '?include_done=true' : ''}`);
}
