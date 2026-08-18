import { useState } from 'react';
import { motion } from 'framer-motion';
import { Github, ExternalLink, Loader2, CheckCircle, AlertCircle, GitPullRequest } from 'lucide-react';
import { Button, Card } from '../components/ui-animated';
import { prApi } from '../api/endpoints/pull-requests';

interface CreatePRButtonProps {
  scanId: string;
  findingIds?: string[];
  onSuccess?: (prUrl: string) => void;
}

type PRStep = 'idle' | 'creating' | 'success' | 'error';

const stepLabels: Record<PRStep, string> = {
  idle: 'Ready to create PR',
  creating: 'Creating Pull Request...',
  success: 'PR created successfully!',
  error: 'Failed to create PR',
};

export function CreatePRButton({ scanId, findingIds, onSuccess }: CreatePRButtonProps) {
  const [step, setStep] = useState<PRStep>('idle');
  const [prUrl, setPrUrl] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleCreatePR = async () => {
    setStep('creating');
    setError('');

    try {
      const response = await prApi.createPR({
        scan_id: scanId,
        finding_ids: findingIds,
        is_draft: false,
      });

      setPrUrl(response.github_pr_url);
      setStep('success');

      if (onSuccess) {
        onSuccess(response.github_pr_url);
      }
    } catch (err: any) {
      console.error('PR creation failed:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to create PR');
      setStep('error');
    }
  };

  const handleReset = () => {
    setStep('idle');
    setError('');
    setPrUrl('');
  };

  if (step === 'success' && prUrl) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="p-6" hover={false}>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <CheckCircle className="h-6 w-6 text-green-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-foreground">Pull Request Created!</h3>
                <p className="text-sm text-muted-foreground">
                  AI-generated fixes have been pushed to a new branch
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="primary"
                onClick={() => window.open(prUrl, '_blank')}
                icon={<ExternalLink className="h-4 w-4" />}
                className="flex-1"
              >
                View on GitHub
              </Button>
              <Button
                variant="secondary"
                onClick={handleReset}
                icon={<GitPullRequest className="h-4 w-4" />}
              >
                Create Another
              </Button>
            </div>
          </div>
        </Card>
      </motion.div>
    );
  }

  if (step === 'error') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="p-6 border-red-500/30 bg-red-500/10" hover={false}>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/20">
                <AlertCircle className="h-6 w-6 text-red-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-400">PR Creation Failed</h3>
                <p className="text-sm text-red-300">{error}</p>
              </div>
            </div>

            <Button
              variant="secondary"
              onClick={handleReset}
              icon={<GitPullRequest className="h-4 w-4" />}
              className="w-full"
            >
              Try Again
            </Button>
          </div>
        </Card>
      </motion.div>
    );
  }

  if (step === 'creating') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="p-6" hover={false}>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/20">
                <Loader2 className="h-6 w-6 text-primary animate-spin" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-foreground">{stepLabels.creating}</h3>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    );
  }

  return (
    <Card className="p-6" hover={false}>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
            <Github className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-foreground">Automated Pull Request</h3>
            <p className="text-sm text-muted-foreground">
              Create a PR with AI-generated fixes
            </p>
          </div>
        </div>

        <Button
          variant="primary"
          onClick={handleCreatePR}
          icon={<GitPullRequest className="h-5 w-5" />}
          size="lg"
          className="w-full"
        >
          Create Pull Request
        </Button>

        <p className="text-xs text-center text-muted-foreground">
          This will create a new branch, apply fixes, and open a PR on GitHub
        </p>
      </div>
    </Card>
  );
}
