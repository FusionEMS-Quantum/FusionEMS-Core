import './globals.css';
import { ReactNode } from 'react';
import { AuthProvider } from '@/components/AuthProvider';
import { WSBootstrap } from '@/components/WSBootstrap';
import { Providers } from './providers';
import QuantumCanvasBackdrop from '@/components/ambient/QuantumCanvasBackdrop';

export const metadata = {
  title: 'FusionEMS Quantum',
  description: 'Enterprise EMS Revenue + Operations OS',
  icons: {
    icon: '/brand/favicon.svg',
    shortcut: '/brand/favicon.svg',
    apple: '/brand/favicon.svg',
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        {/* Global ambient background — fixed, sits behind all page content */}
        <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden bg-[linear-gradient(180deg,#040507_0%,#0a0c0e_38%,#050608_100%)]" aria-hidden="true">
          <QuantumCanvasBackdrop mode="global" intensity={1} />
          <div className="absolute inset-x-0 top-0 h-[42vh] bg-[radial-gradient(circle_at_top,rgba(255,124,37,0.16),transparent_62%)]" />
          <div className="absolute inset-x-0 bottom-0 h-[28vh] bg-[radial-gradient(circle_at_bottom_left,rgba(255,96,32,0.12),transparent_58%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(5,7,11,0.05),rgba(5,7,11,0.3))]" />
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
