type BillingInterval = 'monthly' | 'yearly'

interface CheckoutPayload {
  plan: string
  billing?: BillingInterval
  coupon?: string
  gateway?: 'stripe' | 'razorpay'
}

interface CheckoutResponse {
  gateway?: string
  checkout_url?: string
  session_url?: string
  session_id?: string
  key?: string
  order_id?: string
  amount?: number
  currency?: string
  plan?: string
  billing_interval?: BillingInterval
  mock?: boolean
}

interface RazorpaySuccessPayload {
  payment_id: string
  order_id: string
  signature: string
}

interface RazorpayVerifyResponse {
  success: boolean
  payment_id: string
  order_id?: string
  subscription_id?: string
  plan: string
  status: string
  current_period_end?: string
  message?: string
}

interface RazorpayHandlerResponse {
  razorpay_payment_id?: string
  razorpay_order_id?: string
  razorpay_signature?: string
}

interface RazorpayCheckoutOptions {
  key: string
  amount: number
  currency: string
  order_id: string
  name: string
  description: string
  handler: (response: RazorpayHandlerResponse) => Promise<void>
  modal?: {
    ondismiss?: () => void
  }
  theme?: {
    color?: string
  }
}

type RazorpayInstance = {
  open: () => void
}

type RazorpayConstructor = new (options: RazorpayCheckoutOptions) => RazorpayInstance

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor
  }
}

const CHECKOUT_URL = '/api/payment/checkout'
const VERIFY_URL = '/api/payment/verify'
const RAZORPAY_SCRIPT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'

let razorpayScriptPromise: Promise<void> | null = null

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') {
      return data.detail
    }
    if (typeof data?.message === 'string') {
      return data.message
    }
  } catch {
    // Ignore JSON parsing errors and fall back to status text.
  }

  return response.statusText || 'Request failed'
}

function getAccessToken(explicitToken?: string): string {
  const token = explicitToken || localStorage.getItem('access_token') || ''
  if (!token) {
    throw new Error('Authentication required for payment verification')
  }
  return token
}

function buildAuthHeaders(token?: string): HeadersInit {
  const accessToken = getAccessToken(token)
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${accessToken}`,
  }
}

function buildSuccessUrl(plan: string) {
  const params = new URLSearchParams({
    gateway: 'razorpay',
    verified: 'true',
    plan,
  })
  return `/billing/success?${params.toString()}`
}

async function loadRazorpayScript(): Promise<void> {
  if (window.Razorpay) {
    return
  }

  if (!razorpayScriptPromise) {
    razorpayScriptPromise = new Promise<void>((resolve, reject) => {
      const existingScript = document.querySelector<HTMLScriptElement>(`script[src="${RAZORPAY_SCRIPT_SRC}"]`)
      if (existingScript) {
        if (window.Razorpay) {
          resolve()
          return
        }
        existingScript.addEventListener('load', () => resolve(), { once: true })
        existingScript.addEventListener('error', () => reject(new Error('Failed to load Razorpay checkout script')), { once: true })
        return
      }

      const script = document.createElement('script')
      script.src = RAZORPAY_SCRIPT_SRC
      script.async = true
      script.onload = () => resolve()
      script.onerror = () => reject(new Error('Failed to load Razorpay checkout script'))
      document.body.appendChild(script)
    })
  }

  await razorpayScriptPromise
}

export async function createCheckout(payload: CheckoutPayload, token?: string): Promise<CheckoutResponse> {
  const response = await fetch(CHECKOUT_URL, {
    method: 'POST',
    headers: buildAuthHeaders(token),
    body: JSON.stringify({
      plan: payload.plan,
      billing: payload.billing || 'monthly',
      coupon: payload.coupon,
      gateway: payload.gateway,
    }),
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

export async function verifyRazorpayPayment(
  payload: RazorpaySuccessPayload,
  token?: string,
): Promise<RazorpayVerifyResponse> {
  const response = await fetch(VERIFY_URL, {
    method: 'POST',
    headers: buildAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

async function openRazorpayCheckout(data: CheckoutResponse): Promise<void> {
  const key = data.key
  const orderId = data.order_id
  const amount = data.amount
  const currency = data.currency
  const plan = data.plan || 'plus'

  if (!key || !orderId || amount == null || !currency) {
    throw new Error('Incomplete Razorpay checkout payload from backend')
  }

  await loadRazorpayScript()

  const Razorpay = window.Razorpay
  if (!Razorpay) {
    throw new Error('Razorpay checkout is unavailable')
  }

  return new Promise<void>((resolve, reject) => {
    const checkout = new Razorpay({
      key,
      amount,
      currency,
      order_id: orderId,
      name: 'DevArchAI',
      description: `${plan.toUpperCase()} subscription`,
      handler: async (response) => {
        const paymentId = response.razorpay_payment_id
        const orderId = response.razorpay_order_id
        const signature = response.razorpay_signature

        if (!paymentId || !orderId || !signature) {
          reject(new Error('Missing Razorpay payment confirmation fields'))
          return
        }

        try {
          const verification = await verifyRazorpayPayment({
            payment_id: paymentId,
            order_id: orderId,
            signature,
          })

          window.location.assign(buildSuccessUrl(verification.plan || plan))
          resolve()
        } catch (error) {
          reject(error instanceof Error ? error : new Error('Payment verification failed'))
        }
      },
      modal: {
        ondismiss: () => reject(new Error('Payment cancelled')),
      },
      theme: {
        color: '#0f766e',
      },
    })

    checkout.open()
  })
}

export async function handleCheckoutResponse(data: CheckoutResponse): Promise<void> {
  const redirectUrl = data.session_url || data.checkout_url

  if (data.gateway === 'razorpay' || (!!data.order_id && !!data.key)) {
    await openRazorpayCheckout(data)
    return
  }

  if (redirectUrl) {
    window.location.assign(redirectUrl)
    return
  }

  throw new Error('Unsupported payment checkout response')
}
