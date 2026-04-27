import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Github, ExternalLink, Loader2, CheckCircle, AlertCircle, GitBranch, FileCode, Upload, GitPullRequest } from 'lucide-react';
import { Button, Card } from '../components/ui-animated';
import { prApi } from '../api/endpoints/pull-requests';

interface CreatePRButtonProps {
  scanId: string;
  findingIds?: string[];
  scoreBefore: number;
  scoreAfter: number;
  onSuccess?: (prUrl: string) => void;
}

type PRStep = 
  | 'idle'
  | 'preparing'
  | 'cloning'
  | 'applying_fixes'
  | 'creating_branch'
  | 'committing'
  | 'pushing'
  | 'creating_pr'
  | 'success'
  | 'error';

const stepLabels: Record<PRStep, string> = {
  idle: 'Ready to create PR',
  preparing: 'Preparing fixes...',
  cloning: 'Cloning repository...',
  applying_fixes: 'Applying AI fixes...',
  creating_branch: 'Creating branch...',
  committing: 'Committing changes...',
  pushing: 'Pushing to GitHub...',
  creating_pr: 'Creating Pull Request...',
  success: 'PR created successfully!',
  error: 'Failed to create PR',
};

const stepIcons: Record<PRStep, React.ReactNode> = {
  idle: <GitPullRequest className="h-5 w-5" />,
  preparing: <FileCode className="h-5 w-5" />,
  cloning: <GitBranch className="h-5 w-5" />,
  applying_fixes: <FileCode className="h-5 w-5" />,
  creating_branch: <GitBranch className="h-5 w-5" />,
  committing: <Upload className="h-5 w-5" />,
  pushing: <Upload className="h-5 w-5" />,
  creating_pr: <GitPullRequest className="h-5 w-5" />,
  success: <CheckCircle className="h-5 w-5" />,
  error: <AlertCircle className="h-5 w-5" />,
};

export function CreatePRButton({ scanId, findingIds, scoreBefore, scoreAfter, onSuccess }: CreatePRButtonProps) {
  const [step, setStep] = useState<PRStep>('idle');
  const [prUrl, setPrUrl] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [progress, setProgress] = useState(0);
  const progressIntervalRef = useRef<number | null>(null);
  const stepTimeoutsRef = useRef<number[]>([]);

  const isProcessing = step !== 'idle' && step !== 'success' && step !== 'error';

  const clearProgressTimers = () => {
    if (progressIntervalRef.current !== null) {
      window.clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }

    stepTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
    stepTimeoutsRef.current = [];
  };

  useEffect(() => {
    return () => {
      clearProgressTimers();
    };
  }, []);

  const handleCreatePR = async () => {
    clearProgressTimers();
    setStep('preparing');
    setError('');
    setProgress(0);

    try {
      // Simulate progress updates for better UX
      progressIntervalRef.current = window.setInterval(() => {
        setProgress(prev => {
          if (prev >= 95) {
            if (progressIntervalRef.current !== null) {
              window.clearInterval(progressIntervalRef.current);
              progressIntervalRef.current = null;
            }
            return 95;
          }
          return prev + 5;
        });
      }, 500);

      // Update steps based on typical timing
      stepTimeoutsRef.current = [
        window.setTimeout(() => setStep('cloning'), 500),
        window.setTimeout(() => setStep('applying_fixes'), 2000),
        window.setTimeout(() => setStep('creating_branch'), 4000),
        window.setTimeout(() => setStep('committing'), 6000),
        window.setTimeout(() => setStep('pushing'), 8000),
        window.setTimeout(() => setStep('creating_pr'), 10000),
      ];

      const response = await prApi.createPR({
        scan_id: scanId,
        finding_ids: findingIds,
        is_draft: false,
      });

      clearProgressTimers();
      setProgress(100);
      setPrUrl(response.github_pr_url);
      setStep('success');

      if (onSuccess) {
        onSuccess(response.github_pr_url);
      }
    } catch (err: any) {
      clearProgressTimers();
      console.error('PR creation failed:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to create PR');
      setStep('error');
    }
  };

  const handleReset = () => {
    clearProgressTimers();
    setStep('idle');
    setError('');
    setPrUrl('');
    setProgress(0);
  };

  // Success state
  if (step === 'success' && prUrl) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="p-6 glow-primary" hover={false}>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <CheckCircle className="h-6 w-6 text-green-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-foreground">Pull Request Created!</h3>
                <p className="text-sm text-muted-foreground">
                  Score improvement: {scoreBefore.toFixed(1)} → {scoreAfter.toFixed(1)} (+{(scoreAfter - scoreBefore).toFixed(1)})
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

  // Error state
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

  // Processing state
  if (isProcessing) {
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
                <h3 className="text-lg font-semibold text-foreground">Creating Pull Request</h3>
                <p className="text-sm text-muted-foreground">{stepLabels[step]}</p>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-primary to-indigo-600"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>

            {/* Step indicators */}
            <div className="grid grid-cols-4 gap-2 text-xs">
              {(['preparing', 'applying_fixes', 'pushing', 'creating_pr'] as PRStep[]).map((s, idx) => {
                const stepOrder = ['preparing', 'cloning', 'applying_fixes', 'creating_branch', 'committing', 'pushing', 'creating_pr'];
                const currentIdx = stepOrder.indexOf(step);
                const stepIdx = stepOrder.indexOf(s);
                const isComplete = currentIdx > stepIdx;
                const isCurrent = step === s;

                return (
                  <div
                    key={s}
                    className={`flex items-center gap-1 p-2 rounded ${
                      isComplete ? 'bg-green-500/20 text-green-400' :
                      isCurrent ? 'bg-primary/20 text-primary' :
                      'bg-white/5 text-muted-foreground'
                    }`}
                  >
                    {isComplete ? <CheckCircle className="h-3 w-3" /> : stepIcons[s]}
                    <span className="truncate">{stepLabels[s].replace('...', '')}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      </motion.div>
    );
  }

  // Idle state - show button
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
              Create a PR with AI-generated fixes ({findingIds?.length || 'all critical + high'} issues)
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
          <div className="text-sm">
            <span className="text-muted-foreground">Score improvement:</span>
            <span className="ml-2 font-semibold text-primary">
              {scoreBefore.toFixed(1)} → {scoreAfter.toFixed(1)} (+{(scoreAfter - scoreBefore).toFixed(1)})
            </span>
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
