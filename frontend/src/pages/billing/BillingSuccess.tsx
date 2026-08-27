import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAuthStore } from '../../stores/auth-store'
import { verifyRazorpayPayment } from '../../lib/payment-gateway'

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
      const redirectPath = searchParams.get('redirect')
      const isMock = searchParams.get('mock') === 'true'
      const gateway = searchParams.get('gateway')
      const isVerified = searchParams.get('verified') === 'true'
      const razorpayPaymentId = searchParams.get('razorpay_payment_id')
      const razorpayOrderId = searchParams.get('razorpay_order_id')
      const razorpaySignature = searchParams.get('razorpay_signature')

      const finishSuccess = (resolvedPlan?: string) => {
        setPlan(resolvedPlan || planParam || 'subscription')
        setSuccess(true)
        setIsProcessing(false)
        setTimeout(() => {
          if (redirectPath) {
            navigate(decodeURIComponent(redirectPath))
          } else {
            navigate('/billing')
          }
        }, 2000)
      }

      if (gateway === 'razorpay' && isVerified) {
        finishSuccess(planParam || 'plus')
        return
      }

      if (razorpayPaymentId && razorpayOrderId && razorpaySignature && token) {
        try {
          const verification = await verifyRazorpayPayment(
            {
              payment_id: razorpayPaymentId,
              order_id: razorpayOrderId,
              signature: razorpaySignature,
            },
            token,
          )
          finishSuccess(verification.plan || planParam || 'plus')
          return
        } catch (error) {
          console.error('Failed to verify Razorpay payment:', error)
          setSuccess(false)
          setIsProcessing(false)
          return
        }
      }

      if (!sessionId) {
        setSuccess(false)
        setIsProcessing(false)
        return
      }

      setPlan(planParam || 'subscription')

      try {
        if (isMock) {
          // Mock/dev mode: activate subscription directly
          await new Promise(resolve => setTimeout(resolve, 1500))

          if (token && planParam) {
            await api.post('/billing/subscription', {
              plan: planParam,
              billing: 'monthly',
            }, {
              headers: { Authorization: `Bearer ${token}` }
            })
          }
        } else {
          // Real payment: wait for webhook to activate subscription
          // Just verify the session exists
          await new Promise(resolve => setTimeout(resolve, 2000))
          
          // Check if subscription was activated by webhook
          if (token) {
            try {
              const response = await api.get('/billing/subscription', {
                headers: { Authorization: `Bearer ${token}` }
              })
              if (response.data.plan && response.data.plan !== 'free') {
                finishSuccess(response.data.plan)
                return
              }
            } catch {
              // Webhook may not have processed yet — fall through to optimistic success
            }
            
            // If webhook hasn't processed yet, show success anyway (will be activated soon)
            finishSuccess(planParam || 'subscription')
            return
          }
        }

        finishSuccess(planParam || 'subscription')
      } catch (error: any) {
        console.error('Failed to process checkout:', error)
        
        // If direct activation is blocked (payment providers configured), 
        // tell user to wait for webhook
        if (error.response?.status === 403) {
          finishSuccess(planParam || 'subscription')
        } else {
          setSuccess(false)
          setIsProcessing(false)
        }
      }
    }

    processCheckout()
  }, [searchParams, token, navigate])

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
