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
export type EventTaskStatus = 'TODO' | 'IN_PROGRESS' | 'DONE';
export type NotificationType =
  | 'REGISTRATION_CONFIRMED'
  | 'REGISTRATION_WAITLISTED'
  | 'WAITLIST_PROMOTED'
  | 'EVENT_UPDATED'
  | 'EVENT_CANCELLED'
  | 'EVENT_ANNOUNCEMENT'
  | 'EVENT_REMINDER'
  | 'FEEDBACK_REQUESTED'
  | 'TASK_ASSIGNED';

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
  checked_in_at: string | null;
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
  qr_url: string | null;
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

// ── Organizations (self-service) ──

export interface OrganizationUpdateRequest {
  name?: string;
  description?: string | null;
  contact_email?: string | null;
}

export interface OrganizationMemberDetail {
  user_id: string;
  full_name: string;
  email: string;
  role: OrgRole;
}

export interface OrganizationMemberAddRequest {
  email: string;
  role: OrgRole;
}

// ── Notifications & announcements ──

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  event_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
}

export interface AnnouncementCreateRequest {
  title: string;
  message: string;
}

export interface AnnouncementResponse {
  id: string;
  event_id: string;
  title: string;
  message: string;
  author_name: string;
  created_at: string;
  recipients: number | null;
}

// ── Feedback & report ──

export interface FeedbackRequest {
  rating: number;
  comment?: string | null;
}

export interface FeedbackResponse {
  id: string;
  event_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackComment {
  rating: number;
  comment: string;
  created_at: string;
}

export interface EventReportResponse {
  event_id: string;
  title: string;
  status: EventStatus;
  attendance: AttendanceStatsResponse;
  feedback_count: number;
  average_rating: number | null;
  rating_distribution: Record<string, number>;
  feedback_response_rate: number;
  comments: FeedbackComment[];
}

// ── Event team tasks ──

export interface EventTaskRequest {
  title?: string;
  description?: string | null;
  assignee_id?: string | null;
  due_at?: string | null;
  status?: EventTaskStatus;
}

export interface EventTask {
  id: string;
  event_id: string;
  title: string;
  description: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
  status: EventTaskStatus;
  due_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MyTask extends EventTask {
  event: TicketEventSummary;
}

export interface TicketVerificationResponse {
  ticket_id: string;
  state: TicketState;
  event: TicketEventSummary;
  checked_in_at: string | null;
  attendee_name: string | null;
  can_check_in: boolean;
  check_in_unavailable_reason: string | null;
}
