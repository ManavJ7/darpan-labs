'use client';

import { InterviewContainer } from '@/components/interview';

interface PageProps {
  params: { sessionId: string };
}

export default function InterviewSessionPage({ params }: PageProps) {
  const { sessionId } = params;

  // For resume, we don't need a userId since the session already exists
  // The backend will look up the user from the session
  return <InterviewContainer sessionId={sessionId} userId="" />;
}
