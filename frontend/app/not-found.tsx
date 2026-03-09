import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="max-w-md w-full text-center space-y-4">
        <h1 className="text-6xl font-bold text-white">404</h1>
        <p className="text-gray-400 text-sm">Page not found. This route does not exist in FusionEMS.</p>
        <Link
          href="/"
          className="inline-block px-5 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition-colors"
        >
          Go Home
        </Link>
      </div>
    </div>
  );
}
