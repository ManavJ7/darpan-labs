/**
 * Interview API functions.
 */

import { api } from './api';
import type {
  InterviewStartRequest,
  InterviewStartResponse,
  InterviewAnswerRequest,
  InterviewAnswerResponse,
  InterviewNextQuestionResponse,
  InterviewStatusResponse,
  InterviewSkipRequest,
  InterviewPauseResponse,
  UserModulesResponse,
  StartSingleModuleRequest,
  ModuleCompleteResponse,
} from '@/types/interview';

const API_PREFIX = '/api/v1';

/**
 * Start a new interview session.
 */
export async function startInterview(
  request: InterviewStartRequest
): Promise<InterviewStartResponse> {
  return api.post<InterviewStartResponse>(`${API_PREFIX}/interviews/start`, request);
}

/**
 * Submit an answer to the current question.
 */
export async function submitAnswer(
  sessionId: string,
  request: InterviewAnswerRequest
): Promise<InterviewAnswerResponse> {
  return api.post<InterviewAnswerResponse>(
    `${API_PREFIX}/interviews/${sessionId}/answer`,
    request
  );
}

/**
 * Get the next question for the interview.
 */
export async function getNextQuestion(
  sessionId: string
): Promise<InterviewNextQuestionResponse> {
  return api.post<InterviewNextQuestionResponse>(
    `${API_PREFIX}/interviews/${sessionId}/next-question`,
    {}
  );
}

/**
 * Skip the current question.
 */
export async function skipQuestion(
  sessionId: string,
  request?: InterviewSkipRequest
): Promise<InterviewNextQuestionResponse> {
  return api.post<InterviewNextQuestionResponse>(
    `${API_PREFIX}/interviews/${sessionId}/skip`,
    request || {}
  );
}

/**
 * Pause the interview for later resumption.
 */
export async function pauseInterview(
  sessionId: string
): Promise<InterviewPauseResponse> {
  return api.post<InterviewPauseResponse>(
    `${API_PREFIX}/interviews/${sessionId}/pause`,
    {}
  );
}

/**
 * Resume a paused interview.
 */
export async function resumeInterview(
  sessionId: string
): Promise<InterviewStartResponse> {
  return api.post<InterviewStartResponse>(
    `${API_PREFIX}/interviews/${sessionId}/resume`,
    {}
  );
}

/**
 * Get the full status of an interview session.
 */
export async function getInterviewStatus(
  sessionId: string
): Promise<InterviewStatusResponse> {
  return api.get<InterviewStatusResponse>(
    `${API_PREFIX}/interviews/${sessionId}/status`
  );
}

// Local storage helpers for session persistence
const SESSION_STORAGE_KEY = 'darpan_interview_session';

export function saveSessionToStorage(sessionId: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
}

export function getSessionFromStorage(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(SESSION_STORAGE_KEY);
  }
  return null;
}

export function clearSessionFromStorage(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  }
}

// ========== Module-Based Onboarding APIs ==========

/**
 * Get all module completion status for a user.
 */
export async function getUserModules(userId: string): Promise<UserModulesResponse> {
  return api.get<UserModulesResponse>(`${API_PREFIX}/interviews/user/${userId}/modules`);
}

/**
 * Start a specific module for a user.
 */
export async function startSingleModule(
  request: StartSingleModuleRequest
): Promise<InterviewStartResponse> {
  return api.post<InterviewStartResponse>(`${API_PREFIX}/interviews/start-module`, request);
}

/**
 * Complete current module and exit to module selection.
 */
export async function completeModuleAndExit(
  sessionId: string
): Promise<ModuleCompleteResponse> {
  return api.post<ModuleCompleteResponse>(
    `${API_PREFIX}/interviews/${sessionId}/complete-module`,
    {}
  );
}

// Local storage helpers for user ID persistence
const USER_ID_STORAGE_KEY = 'darpan_user_id';

export function saveUserIdToStorage(userId: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(USER_ID_STORAGE_KEY, userId);
  }
}

export function getUserIdFromStorage(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(USER_ID_STORAGE_KEY);
  }
  return null;
}

export function clearUserIdFromStorage(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(USER_ID_STORAGE_KEY);
  }
}
