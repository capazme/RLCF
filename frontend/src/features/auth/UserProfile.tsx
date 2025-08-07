import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';

export function UserProfile() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Profile</h1>
        <p className="text-slate-400">Manage your account and preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12 text-center">
            <div>
              <h3 className="text-lg font-medium text-slate-400 mb-2">
                Profile Management Coming Soon
              </h3>
              <p className="text-sm text-slate-500">
                User profile and settings are being implemented.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}