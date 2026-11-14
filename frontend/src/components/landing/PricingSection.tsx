import { useProductConfigState } from '../../hooks/useProductConfig'

import { BetaAccessSection } from './BetaAccessSection'
import { CommercialPricingSection, PricingSectionSkeleton } from './CommercialPricingSection'

export function PricingSection() {
  const { config, isLoading } = useProductConfigState()

  if (isLoading) {
    return <PricingSectionSkeleton />
  }

  if (config.beta_access_mode) {
    return <BetaAccessSection config={config} />
  }

  return (
    <section className="py-16 lg:py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-7xl mx-auto">
          <CommercialPricingSection />
        </div>
      </div>
    </section>
  )
}
