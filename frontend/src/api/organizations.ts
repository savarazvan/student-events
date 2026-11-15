import { request } from './client';
import type {
  OrganizationMemberAddRequest,
  OrganizationMemberDetail,
  OrganizationResponse,
  OrganizationUpdateRequest,
  OrgRole,
} from '../types';

export function listPublicOrganizations(): Promise<OrganizationResponse[]> {
  return request<OrganizationResponse[]>('GET', '/organizations', undefined, false);
}

export function getOrganization(orgId: string): Promise<OrganizationResponse> {
  return request<OrganizationResponse>('GET', `/organizations/${orgId}`);
}

export function updateOrganization(
  orgId: string,
  data: OrganizationUpdateRequest,
): Promise<OrganizationResponse> {
  return request<OrganizationResponse>('PATCH', `/organizations/${orgId}`, data);
}

export function listOrgMembers(orgId: string): Promise<OrganizationMemberDetail[]> {
  return request<OrganizationMemberDetail[]>('GET', `/organizations/${orgId}/members`);
}

export function addOrgMember(
  orgId: string,
  data: OrganizationMemberAddRequest,
): Promise<OrganizationMemberDetail> {
  return request<OrganizationMemberDetail>('POST', `/organizations/${orgId}/members`, data);
}

export function updateOrgMemberRole(
  orgId: string,
  userId: string,
  role: OrgRole,
): Promise<OrganizationMemberDetail> {
  return request<OrganizationMemberDetail>(
    'PATCH',
    `/organizations/${orgId}/members/${userId}`,
    { role },
  );
}

export function removeOrgMember(orgId: string, userId: string): Promise<void> {
  return request<void>('DELETE', `/organizations/${orgId}/members/${userId}`);
}
