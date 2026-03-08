import './globals.css';
import { ReactNode } from 'react';
import { Barlow, Barlow_Condensed, JetBrains_Mono } from 'next/font/google';
import { AuthProvider } from '@/components/AuthProvider';
import { WSBootstrap } from '@/components/WSBootstrap';
import { Providers } from './providers';

const barlow = Barlow({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '900'],
  variable: '--font-sans',
  display: 'swap',
});

const barlowCondensed = Barlow_Condensed({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '900'],
  variable: '--font-label',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata = {
  title: 'FusionEMS Quantum',
  description: 'Enterprise EMS Revenue + Operations OS',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${barlow.variable} ${barlowCondensed.variable} ${jetbrainsMono.variable}`}>
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
