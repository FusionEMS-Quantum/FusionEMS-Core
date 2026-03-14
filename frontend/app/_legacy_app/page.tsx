import { redirect } from 'next/navigation';

export default function AppRootPage() {
  redirect('/_legacy_app/home');
}
