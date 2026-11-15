// ── Enums ──

export type GlobalRole = 'USER' | 'SUPER_ADMIN';
export type OrgRole = 'ORG_ADMIN' | 'ORGANIZER' | 'MEMBER';
export type EventStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'PUBLISHED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED';
export type EventCategory =
  | 'WORKSHOP'
  | 'CONFERENCE'
  | 'TRAINING'
  | 'SOCIAL'
  | 'VOLUNTEERING'
  | 'COMPETITION'
  | 'OTHER';
export type EventRegistrationStatus = 'CONFIRMED' | 'WAITLIST' | 'CANCELLED';
export type TicketState = 'VALID' | 'USED' | 'REVOKED';

// ── Auth ──

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OrganizationMembership {
  organization_id: string;
  organization_name: string;
  role: OrgRole;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  global_role: GlobalRole;
  is_active: boolean;
  organization_memberships: OrganizationMembership[];
}

// ── Admin ──

export interface OrganizationCreateRequest {
  name: string;
  description?: string | null;
  contact_email: string;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  description: string | null;
  contact_email: string | null;
}

export interface AssignOrgMemberRequest {
  user_id: string;
  role: OrgRole;
}

export interface OrganizationMemberResponse {
  id: string;
  user_id: string;
  organization_id: string;
  role_in_org: OrgRole;
}

export interface UpdateGlobalRoleRequest {
  global_role: GlobalRole;
}

export interface AdminUserResponse {
  id: string;
  email: string;
  full_name: string;
  global_role: GlobalRole;
  is_active: boolean;
}

// ── Events ──

export interface EventCreateRequest {
  title: string;
  description?: string | null;
  location: string;
  start_time: string;
  end_time: string;
  capacity: number;
  organization_id: string;
  image_url?: string | null;
  category?: EventCategory;
  registration_deadline?: string | null;
}

export interface EventUpdateRequest {
  title?: string;
  description?: string | null;
  location?: string;
  start_time?: string;
  end_time?: string;
  capacity?: number;
  image_url?: string | null;
  category?: EventCategory;
  registration_deadline?: string | null;
}

export interface EventStatusUpdateRequest {
  status: EventStatus;
}

export interface EventResponse {
  id: string;
  title: string;
  description: string | null;
  location: string;
  start_time: string;
  end_time: string;
  capacity: number;
  status: EventStatus;
  organization_id: string;
  created_by_id: string;
  created_at: string;
  image_url: string | null;
  category: EventCategory;
  registration_deadline: string | null;
}

export interface PaginatedEventsResponse {
  items: EventResponse[];
  total: number;
  page: number;
  size: number;
}

export interface EventRegistrationResponse {
  id: string;
  event_id: string;
  user_id: string;
  status: EventRegistrationStatus;
  registered_at: string;
  ticket_id: string | null;
}

export interface AttendeeResponse {
  user_id: string;
  full_name: string;
  email: string;
  registered_at: string;
  status: EventRegistrationStatus;
  ticket_id: string | null;
  checked_in_at: string | null;
}

// ── Tickets / Check-in ──

export interface TicketEventSummary {
  id: string;
  title: string;
  location: string;
  start_time: string;
  end_time: string;
  status: EventStatus;
  category: EventCategory;
  organization_id: string;
}

export interface TicketResponse {
  id: string;
  registration_id: string;
  state: TicketState;
  issued_at: string;
  checked_in_at: string | null;
  qr_token: string | null;
  event: TicketEventSummary;
}

export interface MyRegistrationResponse {
  id: string;
  status: EventRegistrationStatus;
  registered_at: string;
  ticket_id: string | null;
  ticket_state: TicketState | null;
  checked_in_at: string | null;
  event: TicketEventSummary;
}

export interface CheckInRequest {
  token: string;
}

export interface ManualCheckInRequest {
  user_id: string;
}

export interface CheckInResponse {
  ticket_id: string;
  user_id: string;
  full_name: string;
  email: string;
  checked_in_at: string;
  checked_in_by_id: string | null;
}

export interface AttendanceStatsResponse {
  event_id: string;
  capacity: number;
  confirmed: number;
  waitlisted: number;
  cancelled: number;
  checked_in: number;
  not_checked_in: number;
  attendance_rate: number;
  spots_left: number;
}

// ── Event list query params ──

export interface EventListParams {
  organization_id?: string;
  status?: EventStatus;
  category?: EventCategory;
  starts_after?: string;
  starts_before?: string;
  search?: string;
  page?: number;
  size?: number;
}
