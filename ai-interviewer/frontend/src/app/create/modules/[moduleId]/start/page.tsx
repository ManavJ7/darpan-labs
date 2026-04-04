'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { ModuleInterviewContainer } from '@/components/interview/ModuleInterviewContainer';

interface PageProps {
  params: { moduleId: string };
}

function ModuleStartContent({ moduleId }: { moduleId: string }) {
  const searchParams = useSearchParams();
  const userId = searchParams.get('userId');

  if (!userId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-darpan-bg">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-white mb-2">Invalid Session</h1>
          <p className="text-white/50">Please start from the modules page.</p>
          <a
            href="/create/modules"
            className="inline-block mt-4 px-4 py-2 bg-darpan-lime text-black font-semibold rounded-lg"
          >
            Go to Modules
          </a>
        </div>
      </div>
    );
  }

  return <ModuleInterviewContainer userId={userId} moduleId={moduleId} />;
}

export default function ModuleStartPage({ params }: PageProps) {
  const { moduleId } = params;

  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-darpan-bg">
          <div className="animate-pulse text-white/50">Loading...</div>
        </div>
      }
    >
      <ModuleStartContent moduleId={moduleId} />
    </Suspense>
  );
}
