'use client';

import { ReactNode } from 'react';
import { ViewportProvider } from '@/components/ui/ResponsiveLayer';
import { ToastProvider } from '@/components/ui/ProductPolish';

/**
 * Client-side providers wrapper.
 * Wraps the application with ViewportProvider (responsive/density detection)
 * and ToastProvider (unified notification system).
 */
export function Providers({ children }: { readonly children: ReactNode }) {
  return (
    <ViewportProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </ViewportProvider>
  );
}
