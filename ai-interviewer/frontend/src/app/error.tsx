'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen bg-darpan-bg flex items-center justify-center">
      <div className="flex flex-col items-center gap-4 max-w-md mx-4 text-center">
        <h2 className="text-xl font-semibold text-white">Something went wrong</h2>
        <p className="text-white/50 text-sm">{error.message}</p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-darpan-lime text-black font-semibold rounded-lg"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
