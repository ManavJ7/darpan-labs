'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export default function ProfilePage() {
  const router = useRouter();
  const { user, isInitialized, isLoading, updateProfile } = useAuthStore();

  const [name, setName] = useState('');
  const [sex, setSex] = useState('');
  const [age, setAge] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isInitialized && !user) {
      router.replace('/login');
    }
    if (user) {
      setName(user.display_name || '');
    }
  }, [isInitialized, user, router]);

  useEffect(() => {
    if (isInitialized && user?.profile_completed) {
      router.replace('/create/modules');
    }
  }, [isInitialized, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim() || !sex || !age) {
      setError('Please fill in all fields.');
      return;
    }

    const ageNum = parseInt(age, 10);
    if (isNaN(ageNum) || ageNum < 13 || ageNum > 120) {
      setError('Please enter a valid age (13-120).');
      return;
    }

    setSubmitting(true);
    try {
      await updateProfile({ display_name: name.trim(), sex, age: ageNum });
      router.push('/create/modules');
    } catch (err) {
      setError('Failed to update profile. Please try again.');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isInitialized || isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="w-8 h-8 text-darpan-lime animate-spin" />
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Complete Your Profile</h1>
        <p className="text-gray-400">Tell us a bit about yourself before we begin.</p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-darpan-surface border border-darpan-border rounded-2xl p-8 max-w-md w-full space-y-6"
      >
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-white/70 mb-2">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white
                       placeholder-white/30 focus:outline-none focus:border-darpan-lime/50"
            placeholder="Your name"
          />
        </div>

        {/* Sex */}
        <div>
          <label className="block text-sm font-medium text-white/70 mb-2">Sex</label>
          <select
            value={sex}
            onChange={(e) => setSex(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white
                       focus:outline-none focus:border-darpan-lime/50"
          >
            <option value="" className="bg-darpan-surface">Select...</option>
            <option value="Male" className="bg-darpan-surface">Male</option>
            <option value="Female" className="bg-darpan-surface">Female</option>
            <option value="Other" className="bg-darpan-surface">Other</option>
            <option value="Prefer not to say" className="bg-darpan-surface">Prefer not to say</option>
          </select>
        </div>

        {/* Age */}
        <div>
          <label className="block text-sm font-medium text-white/70 mb-2">Age</label>
          <input
            type="number"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            min={13}
            max={120}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white
                       placeholder-white/30 focus:outline-none focus:border-darpan-lime/50"
            placeholder="Your age"
          />
        </div>

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-darpan-lime text-black
                     font-semibold rounded-lg hover:bg-darpan-lime/90 transition-colors disabled:opacity-50"
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            'Continue to Interview'
          )}
        </button>
      </form>
    </main>
  );
}
