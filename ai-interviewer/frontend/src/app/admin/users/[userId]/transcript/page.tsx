'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Download, Loader2 } from 'lucide-react';
import {
  getUserTranscript,
  getTranscriptDownloadUrl,
  type TranscriptResponse,
} from '@/lib/adminApi';
import { useAuthStore } from '@/store/authStore';

export default function TranscriptPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.userId as string;
  const token = useAuthStore((s) => s.token);

  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!userId) return;
    getUserTranscript(userId)
      .then(setTranscript)
      .catch((err) => {
        console.error(err);
        setError('Failed to load transcript');
      })
      .finally(() => setIsLoading(false));
  }, [userId]);

  const handleDownload = async (format: 'json' | 'csv') => {
    const url = getTranscriptDownloadUrl(userId, format);
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `transcript_${userId}.${format}`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 text-darpan-lime animate-spin" />
      </div>
    );
  }

  if (error || !transcript) {
    return (
      <div className="flex-1 flex items-center justify-center py-24">
        <p className="text-red-400">{error || 'Transcript not found'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            onClick={() => router.push('/admin')}
            className="flex items-center gap-1 text-sm text-white/50 hover:text-white mb-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to dashboard
          </button>
          <h1 className="text-2xl font-bold text-white">
            {transcript.display_name}
          </h1>
          <p className="text-white/50 text-sm">
            {transcript.email}
            {transcript.sex && ` | ${transcript.sex}`}
            {transcript.age && ` | Age ${transcript.age}`}
            {` | ${transcript.total_turns} turns`}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => handleDownload('json')}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-white/10 hover:bg-white/15
                       text-white rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" />
            JSON
          </button>
          <button
            onClick={() => handleDownload('csv')}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-white/10 hover:bg-white/15
                       text-white rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
        </div>
      </div>

      {/* Transcript by module */}
      <div className="space-y-8">
        {transcript.modules.map((module) => (
          <div key={module.module_id}>
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xs font-mono px-2 py-1 bg-darpan-lime/20 text-darpan-lime rounded">
                {module.module_id}
              </span>
              <h2 className="text-lg font-semibold text-white">
                {module.module_name}
              </h2>
              <span className="text-xs text-white/40">
                {module.status} | {module.turns.length} turns
              </span>
            </div>

            <div className="space-y-3 pl-4 border-l border-darpan-border">
              {module.turns.map((turn, idx) => (
                <div
                  key={`${module.module_id}-${turn.turn_index}-${idx}`}
                  className={`rounded-lg px-4 py-3 ${
                    turn.role === 'interviewer'
                      ? 'bg-white/5'
                      : 'bg-darpan-lime/5 border border-darpan-lime/10'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`text-xs font-medium ${
                        turn.role === 'interviewer'
                          ? 'text-darpan-cyan'
                          : 'text-darpan-lime'
                      }`}
                    >
                      {turn.role === 'interviewer' ? 'Interviewer' : 'Respondent'}
                    </span>
                    <span className="text-xs text-white/20">
                      #{turn.turn_index}
                    </span>
                  </div>
                  <p className="text-sm text-white/80">
                    {turn.role === 'interviewer'
                      ? turn.question_text
                      : turn.answer_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))}

        {transcript.modules.length === 0 && (
          <p className="text-center text-white/30 py-12">
            No interview data yet.
          </p>
        )}
      </div>
    </div>
  );
}
