import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';

export function TaskDetails() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Task Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12 text-center">
            <div>
              <h3 className="text-lg font-medium text-slate-400 mb-2">
                Task Details Coming Soon
              </h3>
              <p className="text-sm text-slate-500">
                Detailed task view is being implemented.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}