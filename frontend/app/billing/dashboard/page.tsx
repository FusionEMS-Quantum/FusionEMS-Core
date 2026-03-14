"use client";
import dynamic from 'next/dynamic';

const DashboardClient = dynamic(() => import('./_page'), { ssr: false });

export default function DashboardPage() {
  return <DashboardClient />;
}
