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
      const redirectPath = searchParams.get('redirect')
      const isMock = searchParams.get('mock') === 'true'

      if (!sessionId || !planParam) {
        setSuccess(false)
        setIsProcessing(false)
        return
      }

      setPlan(planParam)

      try {
        if (isMock) {
          // Mock/dev mode: activate subscription directly
          await new Promise(resolve => setTimeout(resolve, 1500))

          if (token) {
            await axios.post('/api/v1/billing/subscription', {
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
              const response = await axios.get('/api/v1/billing/subscription', {
                headers: { Authorization: `Bearer ${token}` }
              })
              if (response.data.plan && response.data.plan !== 'free') {
                setSuccess(true)
                // Redirect after showing success message
                setTimeout(() => {
                  if (redirectPath) {
                    navigate(decodeURIComponent(redirectPath))
                  } else {
                    navigate('/billing')
                  }
                }, 2000)
                setIsProcessing(false)
                return
              }
            } catch (err) {
              console.log('Subscription not yet activated by webhook')
            }
            
            // If webhook hasn't processed yet, show success anyway (will be activated soon)
            setSuccess(true)
            setTimeout(() => {
              if (redirectPath) {
                navigate(decodeURIComponent(redirectPath))
              } else {
                navigate('/billing')
              }
            }, 2000)
            setIsProcessing(false)
            return
          }
        }

        setSuccess(true)

        // Redirect back to scan results or intended destination after 2 seconds
        setTimeout(() => {
          if (redirectPath) {
            navigate(decodeURIComponent(redirectPath))
          } else {
            navigate('/billing')
          }
        }, 2000)
      } catch (error: any) {
        console.error('Failed to process checkout:', error)
        
        // If direct activation is blocked (payment providers configured), 
        // tell user to wait for webhook
        if (error.response?.status === 403) {
          setSuccess(true)
          setTimeout(() => {
            if (redirectPath) {
              navigate(decodeURIComponent(redirectPath))
            } else {
              navigate('/billing')
            }
          }, 2000)
        } else {
          setSuccess(false)
        }
      } finally {
        setIsProcessing(false)
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
