import { request } from './client';
import type { TicketVerificationResponse } from '../types';

/** Verify a scanned ticket; works signed out, organizers get check-in details. */
export function verifyTicket(token: string): Promise<TicketVerificationResponse> {
  return request<TicketVerificationResponse>(
    'GET',
    `/tickets/verify?token=${encodeURIComponent(token)}`,
  );
}
