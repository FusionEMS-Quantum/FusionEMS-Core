import './globals.css';
import { ReactNode } from 'react';
import { AuthProvider } from '@/components/AuthProvider';
import { WSBootstrap } from '@/components/WSBootstrap';
import { Providers } from './providers';

export const metadata = {
  title: 'FusionEMS Quantum',
  description: 'Enterprise EMS Revenue + Operations OS',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {/* Global ambient background — fixed, sits behind all page content */}
        <div className="fixed inset-0 -z-10 pointer-events-none" aria-hidden="true">
          <div className="absolute left-[-12%] top-[-10%] h-[500px] w-[500px] rounded-full bg-orange-500/[0.06] blur-3xl" />
          <div className="absolute right-[-10%] top-[10%] h-[450px] w-[450px] rounded-full bg-amber-400/[0.06] blur-3xl" />
          <div className="absolute bottom-[-12%] left-[30%] h-[520px] w-[520px] rounded-full bg-orange-600/[0.06] blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:radial-gradient(circle_at_center,black,transparent_80%)]" />
        </div>
        <AuthProvider>
          <Providers>
            <WSBootstrap />
            {children}
          </Providers>
        </AuthProvider>
      </body>
    </html>
  );
}
