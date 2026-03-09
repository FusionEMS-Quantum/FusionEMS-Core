export default function GlobalLoading() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
        <p className="text-sm text-gray-400">Loading FusionEMS…</p>
      </div>
    </div>
  );
}
