import { motion } from "framer-motion"
import { Lightbulb } from "lucide-react"

export function FixRoadmap({ currentScore: _ }: { currentScore: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-4 h-4 text-indigo-400" />
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Recommended Actions
        </h3>
      </div>
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <Lightbulb className="w-8 h-8 text-white/20 mb-3" />
        <p className="text-sm text-white/40">Personalized recommendations will appear after deeper analysis.</p>
      </div>
    </motion.div>
  )
}
