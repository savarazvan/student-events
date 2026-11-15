import { request } from './client';
import type {
  AdminUserResponse,
  AssignOrgMemberRequest,
  OrganizationCreateRequest,
  OrganizationMemberResponse,
  OrganizationResponse,
  UpdateGlobalRoleRequest,
} from '../types';

export function listOrganizations(): Promise<OrganizationResponse[]> {
  return request<OrganizationResponse[]>('GET', '/admin/organizations');
}

export function createOrganization(
  data: OrganizationCreateRequest,
): Promise<OrganizationResponse> {
  return request<OrganizationResponse>('POST', '/admin/organizations', data);
}

export function assignOrgMember(
  orgId: string,
  data: AssignOrgMemberRequest,
): Promise<OrganizationMemberResponse> {
  return request<OrganizationMemberResponse>(
    'POST',
    `/admin/organizations/${orgId}/members`,
    data,
  );
}

export function updateGlobalRole(
  userId: string,
  data: UpdateGlobalRoleRequest,
): Promise<AdminUserResponse> {
  return request<AdminUserResponse>(
    'PATCH',
    `/admin/users/${userId}/global-role`,
    data,
  );
}
