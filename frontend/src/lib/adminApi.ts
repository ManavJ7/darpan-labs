/**
 * Admin API functions.
 */

import { api } from './api';

const API_PREFIX = '/api/v1';

export interface AdminModuleSummary {
  module_id: string;
  status: string;
}

export interface AdminUserSummary {
  user_id: string;
  email: string;
  display_name: string;
  sex: string | null;
  age: number | null;
  created_at: string;
  modules: AdminModuleSummary[];
  completed_module_count: number;
  total_turns: number;
}

export interface AdminUserListResponse {
  users: AdminUserSummary[];
  total_count: number;
  skip: number;
  limit: number;
}

export interface TranscriptTurn {
  turn_index: number;
  role: string;
  question_text: string | null;
  answer_text: string | null;
  module_id: string;
  created_at: string;
}

export interface TranscriptModule {
  module_id: string;
  module_name: string;
  status: string;
  turns: TranscriptTurn[];
}

export interface TranscriptResponse {
  user_id: string;
  display_name: string;
  email: string;
  sex: string | null;
  age: number | null;
  modules: TranscriptModule[];
  total_turns: number;
}

export async function getAdminUsers(
  skip = 0,
  limit = 50
): Promise<AdminUserListResponse> {
  return api.get<AdminUserListResponse>(`${API_PREFIX}/admin/users`, {
    skip: String(skip),
    limit: String(limit),
  });
}

export async function getUserTranscript(
  userId: string
): Promise<TranscriptResponse> {
  return api.get<TranscriptResponse>(
    `${API_PREFIX}/admin/users/${userId}/transcript`
  );
}

export function getTranscriptDownloadUrl(
  userId: string,
  format: 'json' | 'csv' = 'json'
): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  return `${baseUrl}${API_PREFIX}/admin/users/${userId}/transcript/download?format=${format}`;
}
