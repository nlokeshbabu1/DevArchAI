/**
 * Organization API endpoints
 */

import apiClient from './client';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  plan: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface OrganizationCreate {
  name: string;
  slug?: string;
  description?: string;
}

export interface OrganizationUpdate {
  name?: string;
  description?: string;
}

export interface Member {
  id: string;
  user_id: string;
  email: string;
  username: string;
  full_name?: string;
  role: string;
  joined_at?: string;
}

export interface MemberInvite {
  email: string;
  role?: string;
}

export const organizationsApi = {
  /**
   * Get current user's organization
   */
  getCurrentOrganization: async (): Promise<Organization> => {
    const response = await apiClient.get<Organization>('/organizations/me');
    return response.data;
  },

  /**
   * List all organizations user is member of
   */
  listOrganizations: async (): Promise<Organization[]> => {
    const response = await apiClient.get<Organization[]>('/organizations');
    return response.data;
  },

  /**
   * Create new organization
   */
  createOrganization: async (data: OrganizationCreate): Promise<Organization> => {
    const response = await apiClient.post<Organization>('/organizations', data);
    return response.data;
  },

  /**
   * Get organization by ID
   */
  getOrganization: async (orgId: string): Promise<Organization> => {
    const response = await apiClient.get<Organization>(`/organizations/${orgId}`);
    return response.data;
  },

  /**
   * Update organization
   */
  updateOrganization: async (orgId: string, data: OrganizationUpdate): Promise<Organization> => {
    const response = await apiClient.put<Organization>(`/organizations/${orgId}`, data);
    return response.data;
  },

  /**
   * List organization members
   */
  listMembers: async (orgId: string): Promise<Member[]> => {
    const response = await apiClient.get<Member[]>(`/organizations/${orgId}/members`);
    return response.data;
  },

  /**
   * Invite member to organization
   */
  inviteMember: async (orgId: string, data: MemberInvite): Promise<{ message: string }> => {
    const response = await apiClient.post(`/organizations/${orgId}/members/invite`, data);
    return response.data;
  },

  /**
   * Remove member from organization
   */
  removeMember: async (orgId: string, memberId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/organizations/${orgId}/members/${memberId}`);
    return response.data;
  },
};
