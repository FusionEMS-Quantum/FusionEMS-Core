export default function FounderLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-500" />
        <p className="text-xs text-gray-500">Loading Founder Command…</p>
      </div>
    </div>
  );
}
