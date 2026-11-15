import { request, requestBlob } from './client';
import type { MyRegistrationResponse, TicketResponse } from '../types';

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
