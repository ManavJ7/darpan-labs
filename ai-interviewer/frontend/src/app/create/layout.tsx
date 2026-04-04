import { Navbar } from '@/components/navigation';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { ProfileGuard } from '@/components/auth/ProfileGuard';

export default function CreateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <ProfileGuard>
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <main className="flex-1">{children}</main>
        </div>
      </ProfileGuard>
    </AuthGuard>
  );
}
