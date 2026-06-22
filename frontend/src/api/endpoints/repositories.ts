/**
 * Repositories API endpoints
 */

import apiClient from './client';

export interface Repository {
  id: string;
  name: string;
  url: string;
  description?: string;
  default_branch: string;
  is_private: boolean;
  created_at: string;
  updated_at: string;
  scan_count?: number;
  last_scan_at?: string;
  scan_status?: 'pending' | 'processing' | 'completed' | 'failed';
  overall_score?: number;
  tech_stack?: string[];
  issues?: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

export interface GitHubRepository {
  id: string;
  name: string;
  url: string;
  description?: string;
  default_branch: string;
  is_private: boolean;
  language?: string;
  stargazers_count: number;
  forks_count: number;
  updated_at: string;
  source?: 'github';
}

export interface RepositoryListResponse {
  repositories: Repository[];
  total: number;
  page: number;
  page_size: number;
}

export interface RepositoryCreate {
  url: string;
  name?: string;
  description?: string;
}

export interface GitHubRepositoryListResponse {
  github_connected: boolean;
  github_repositories: GitHubRepository[];
  total?: number;
  message?: string;
}

export interface GitLabProject {
  id: string;
  name: string;
  url: string;
  description?: string;
  default_branch: string;
  is_private: boolean;
  language?: string;
  stargazers_count: number;
  forks_count: number;
  updated_at: string;
  source?: 'gitlab';
}

export interface GitLabProjectListResponse {
  gitlab_connected: boolean;
  gitlab_projects: GitLabProject[];
  total?: number;
  message?: string;
}

export interface ImportGitHubRepositoriesResponse {
  imported: Array<{
    id: string;
    name: string;
    url: string;
  }>;
  total: number;
  message: string;
}

export interface ImportGitLabProjectsResponse {
  imported: Array<{
    id: string;
    name: string;
    url: string;
  }>;
  total: number;
  message: string;
}

export const repositoriesApi = {
  /**
   * List all repositories for current user
   */
  listRepositories: async (page: number = 1, page_size: number = 20): Promise<RepositoryListResponse> => {
    const response = await apiClient.get<RepositoryListResponse>(`/repositories?page=${page}&page_size=${page_size}`);
    return response.data;
  },

  /**
   * Add a new repository
   */
  createRepository: async (data: RepositoryCreate): Promise<Repository> => {
    const response = await apiClient.post<Repository>('/repositories', data);
    return response.data;
  },

  /**
   * Get a specific repository
   */
  getRepository: async (repoId: string): Promise<Repository> => {
    const response = await apiClient.get<Repository>(`/repositories/${repoId}`);
    return response.data;
  },

  /**
   * Update a repository
   */
  updateRepository: async (repoId: string, data: Partial<Repository>): Promise<Repository> => {
    const response = await apiClient.put<Repository>(`/repositories/${repoId}`, data);
    return response.data;
  },

  /**
   * Delete a repository
   */
  deleteRepository: async (repoId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/repositories/${repoId}`);
    return response.data;
  },

  /**
   * Trigger a scan for a repository
   * Uses the scans API directly (same as dashboard) for reliability
   */
  triggerScan: async (repoId: string, repoUrl: string, branch: string = 'main'): Promise<{ id: string; status: string }> => {
    const response = await apiClient.post('/scans', {
      repository_id: repoId,
      repository_url: repoUrl,
      branch: branch,
    });
    return response.data;
  },

  /**
   * List importable GitHub repositories for the current OAuth user
   */
  listGitHubRepositories: async (): Promise<GitHubRepositoryListResponse> => {
    const response = await apiClient.get<GitHubRepositoryListResponse>('/github/repos');
    return response.data;
  },

  /**
   * Import selected GitHub repositories into the repository list
   */
  importGitHubRepositories: async (repoIds: number[]): Promise<ImportGitHubRepositoriesResponse> => {
    const response = await apiClient.post<ImportGitHubRepositoriesResponse>('/github/import-repos', repoIds);
    return response.data;
  },

  /**
   * List importable GitLab projects for the current OAuth user
   */
  listGitLabProjects: async (): Promise<GitLabProjectListResponse> => {
    const response = await apiClient.get<GitLabProjectListResponse>('/gitlab/projects');
    return response.data;
  },

  /**
   * Import selected GitLab projects into the repository list
   */
  importGitLabProjects: async (projectIds: number[]): Promise<ImportGitLabProjectsResponse> => {
    const response = await apiClient.post<ImportGitLabProjectsResponse>('/gitlab/import-projects', projectIds);
    return response.data;
  },
};
