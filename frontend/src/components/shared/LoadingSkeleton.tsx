import { motion } from 'framer-motion'

export default function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="h-6 bg-slate-800 rounded"
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.2 }}
        />
      ))}
    </div>
  )
}
