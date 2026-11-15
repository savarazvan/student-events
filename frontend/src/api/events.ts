import { request } from './client';
import type {
  AnnouncementCreateRequest,
  AnnouncementResponse,
  AttendanceStatsResponse,
  AttendeeResponse,
  CheckInRequest,
  CheckInResponse,
  EventCreateRequest,
  EventListParams,
  EventRegistrationResponse,
  EventResponse,
  EventReportResponse,
  EventStatusUpdateRequest,
  EventTask,
  EventTaskRequest,
  EventUpdateRequest,
  FeedbackRequest,
  FeedbackResponse,
  ManualCheckInRequest,
  PaginatedEventsResponse,
} from '../types';

export function listEvents(
  params?: EventListParams,
): Promise<PaginatedEventsResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    }
  }
  const qs = searchParams.toString();
  return request<PaginatedEventsResponse>(
    'GET',
    `/events${qs ? `?${qs}` : ''}`,
  );
}

export function getEvent(eventId: string): Promise<EventResponse> {
  return request<EventResponse>('GET', `/events/${eventId}`);
}

export function createEvent(
  data: EventCreateRequest,
): Promise<EventResponse> {
  return request<EventResponse>('POST', '/events', data);
}

export function updateEvent(
  eventId: string,
  data: EventUpdateRequest,
): Promise<EventResponse> {
  return request<EventResponse>('PUT', `/events/${eventId}`, data);
}

export function updateEventStatus(
  eventId: string,
  data: EventStatusUpdateRequest,
): Promise<EventResponse> {
  return request<EventResponse>(
    'PATCH',
    `/events/${eventId}/status`,
    data,
  );
}

export function getMyRegistration(
  eventId: string,
): Promise<EventRegistrationResponse> {
  return request<EventRegistrationResponse>(
    'GET',
    `/events/${eventId}/register`,
  );
}

export function registerForEvent(
  eventId: string,
): Promise<EventRegistrationResponse> {
  return request<EventRegistrationResponse>(
    'POST',
    `/events/${eventId}/register`,
  );
}

export function cancelRegistration(
  eventId: string,
): Promise<EventRegistrationResponse> {
  return request<EventRegistrationResponse>(
    'DELETE',
    `/events/${eventId}/register`,
  );
}

export function getAttendees(
  eventId: string,
): Promise<AttendeeResponse[]> {
  return request<AttendeeResponse[]>(
    'GET',
    `/events/${eventId}/attendees`,
  );
}

export function checkIn(
  eventId: string,
  data: CheckInRequest,
): Promise<CheckInResponse> {
  return request<CheckInResponse>(
    'POST',
    `/events/${eventId}/check-in`,
    data,
  );
}

export function manualCheckIn(
  eventId: string,
  data: ManualCheckInRequest,
): Promise<CheckInResponse> {
  return request<CheckInResponse>(
    'POST',
    `/events/${eventId}/check-in/manual`,
    data,
  );
}

export function undoCheckIn(
  eventId: string,
  ticketId: string,
): Promise<void> {
  return request<void>(
    'DELETE',
    `/events/${eventId}/check-in/${ticketId}`,
  );
}

export function getAttendanceStats(
  eventId: string,
): Promise<AttendanceStatsResponse> {
  return request<AttendanceStatsResponse>(
    'GET',
    `/events/${eventId}/attendance`,
  );
}

// ── Announcements ──

export function listAnnouncements(eventId: string): Promise<AnnouncementResponse[]> {
  return request<AnnouncementResponse[]>('GET', `/events/${eventId}/announcements`);
}

export function createAnnouncement(
  eventId: string,
  data: AnnouncementCreateRequest,
): Promise<AnnouncementResponse> {
  return request<AnnouncementResponse>('POST', `/events/${eventId}/announcements`, data);
}

// ── Feedback & report ──

export function submitFeedback(
  eventId: string,
  data: FeedbackRequest,
): Promise<FeedbackResponse> {
  return request<FeedbackResponse>('PUT', `/events/${eventId}/feedback`, data);
}

export function getMyFeedback(eventId: string): Promise<FeedbackResponse> {
  return request<FeedbackResponse>('GET', `/events/${eventId}/feedback/me`);
}

export function getEventReport(eventId: string): Promise<EventReportResponse> {
  return request<EventReportResponse>('GET', `/events/${eventId}/report`);
}

// ── Event team tasks ──

export function listTasks(eventId: string): Promise<EventTask[]> {
  return request<EventTask[]>('GET', `/events/${eventId}/tasks`);
}

export function createTask(eventId: string, data: EventTaskRequest): Promise<EventTask> {
  return request<EventTask>('POST', `/events/${eventId}/tasks`, data);
}

export function updateTask(
  eventId: string,
  taskId: string,
  data: EventTaskRequest,
): Promise<EventTask> {
  return request<EventTask>('PATCH', `/events/${eventId}/tasks/${taskId}`, data);
}

export function deleteTask(eventId: string, taskId: string): Promise<void> {
  return request<void>('DELETE', `/events/${eventId}/tasks/${taskId}`);
}
