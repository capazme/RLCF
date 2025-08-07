import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';

export function TaskEvaluation() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Task Evaluation</h1>
        <p className="text-slate-400">Evaluate AI responses for legal tasks</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Task Evaluation Interface</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12 text-center">
            <div>
              <h3 className="text-lg font-medium text-slate-400 mb-2">
                Evaluation Interface Coming Soon
              </h3>
              <p className="text-sm text-slate-500">
                The task evaluation wizard is being implemented.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}