import { request } from './client';
import type {
  AttendanceStatsResponse,
  AttendeeResponse,
  CheckInRequest,
  CheckInResponse,
  EventCreateRequest,
  EventListParams,
  EventRegistrationResponse,
  EventResponse,
  EventStatusUpdateRequest,
  EventUpdateRequest,
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
