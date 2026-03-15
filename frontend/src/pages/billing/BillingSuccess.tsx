import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../../stores/auth-store'

export function BillingSuccess() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { token } = useAuthStore()
  const [isProcessing, setIsProcessing] = useState(true)
  const [success, setSuccess] = useState<boolean | null>(null)
  const [plan, setPlan] = useState<string>('')

  useEffect(() => {
    const processCheckout = async () => {
      const sessionId = searchParams.get('session_id')
      const planParam = searchParams.get('plan')

      if (!sessionId || !planParam) {
        setSuccess(false)
        setIsProcessing(false)
        return
      }

      setPlan(planParam)

      try {
        // In production, verify the session with backend
        // For mock, just simulate success
        await new Promise(resolve => setTimeout(resolve, 2000))

        // Update subscription on backend
        if (token) {
          await axios.post('/api/v1/billing/subscription', {
            plan: planParam,
          }, {
            headers: { Authorization: `Bearer ${token}` }
          })
        }

        setSuccess(true)
      } catch (error) {
        console.error('Failed to process checkout:', error)
        setSuccess(false)
      } finally {
        setIsProcessing(false)
      }
    }

    processCheckout()
  }, [searchParams, token])

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Card className="p-8 max-w-md w-full text-center">
        {isProcessing ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
          >
            <Loader2 className="h-16 w-16 animate-spin text-primary mx-auto" />
            <div>
              <h2 className="text-2xl font-bold text-foreground">Processing Payment</h2>
              <p className="text-muted-foreground mt-2">
                Please wait while we activate your {plan} plan...
              </p>
            </div>
          </motion.div>
        ) : success ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
          >
            <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto" />
            <div>
              <h2 className="text-2xl font-bold text-foreground">Payment Successful!</h2>
              <p className="text-muted-foreground mt-2">
                Your {plan} plan has been activated.
              </p>
            </div>
            <Button
              variant="primary"
              onClick={() => navigate('/billing')}
              className="w-full"
            >
              View Subscription
            </Button>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
          >
            <XCircle className="h-16 w-16 text-red-500 mx-auto" />
            <div>
              <h2 className="text-2xl font-bold text-foreground">Payment Failed</h2>
              <p className="text-muted-foreground mt-2">
                Something went wrong. Please try again.
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => navigate('/billing')}
                className="flex-1"
              >
                Back to Plans
              </Button>
              <Button
                variant="primary"
                onClick={() => navigate('/billing')}
                className="flex-1"
              >
                Try Again
              </Button>
            </div>
          </motion.div>
        )}
      </Card>
    </div>
  )
}
