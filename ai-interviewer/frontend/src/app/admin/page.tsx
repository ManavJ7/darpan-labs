'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Download, Eye } from 'lucide-react';
import {
  getAdminUsers,
  getTranscriptDownloadUrl,
  type AdminUserSummary,
  type AdminUserListResponse,
} from '@/lib/adminApi';
import { useAuthStore } from '@/store/authStore';

const MODULE_IDS = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'];

export default function AdminPage() {
  const [data, setData] = useState<AdminUserListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    getAdminUsers(0, 100)
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError('Failed to load users');
      })
      .finally(() => setIsLoading(false));
  }, []);

  const handleDownload = async (userId: string, format: 'json' | 'csv') => {
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

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center py-24">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  const users = data?.users || [];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
        <p className="text-white/50 text-sm mt-1">
          {data?.total_count || 0} total respondents
        </p>
      </div>

      <div className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-darpan-border text-left text-white/50">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Sex</th>
                <th className="px-4 py-3 font-medium">Age</th>
                <th className="px-4 py-3 font-medium">Modules</th>
                <th className="px-4 py-3 font-medium">Q&A</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <UserRow
                  key={user.user_id}
                  user={user}
                  onDownload={handleDownload}
                />
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-white/30">
                    No respondents yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function UserRow({
  user,
  onDownload,
}: {
  user: AdminUserSummary;
  onDownload: (userId: string, format: 'json' | 'csv') => void;
}) {
  const moduleStatusMap = new Map(
    user.modules.map((m) => [m.module_id, m.status])
  );

  return (
    <tr className="border-b border-darpan-border/50 hover:bg-white/[0.02]">
      <td className="px-4 py-3 text-white font-medium">{user.display_name}</td>
      <td className="px-4 py-3 text-white/60">{user.email}</td>
      <td className="px-4 py-3 text-white/60">{user.sex || '-'}</td>
      <td className="px-4 py-3 text-white/60">{user.age ?? '-'}</td>
      <td className="px-4 py-3">
        <div className="flex gap-1 flex-wrap">
          {MODULE_IDS.map((mid) => {
            const status = moduleStatusMap.get(mid);
            let color = 'bg-white/10 text-white/30';
            if (status === 'completed') color = 'bg-darpan-lime/20 text-darpan-lime';
            else if (status === 'active') color = 'bg-darpan-cyan/20 text-darpan-cyan';
            return (
              <span
                key={mid}
                className={`px-1.5 py-0.5 rounded text-xs font-mono ${color}`}
              >
                {mid}
              </span>
            );
          })}
        </div>
      </td>
      <td className="px-4 py-3 text-white/60">{user.total_turns}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Link
            href={`/admin/users/${user.user_id}/transcript`}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-white/10 hover:bg-white/15
                       text-white rounded transition-colors"
          >
            <Eye className="w-3 h-3" />
            View
          </Link>
          <button
            onClick={() => onDownload(user.user_id, 'json')}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-white/10 hover:bg-white/15
                       text-white rounded transition-colors"
          >
            <Download className="w-3 h-3" />
            JSON
          </button>
          <button
            onClick={() => onDownload(user.user_id, 'csv')}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-white/10 hover:bg-white/15
                       text-white rounded transition-colors"
          >
            <Download className="w-3 h-3" />
            CSV
          </button>
        </div>
      </td>
    </tr>
  );
}
