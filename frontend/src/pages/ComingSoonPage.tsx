import { motion } from 'framer-motion'

interface ComingSoonPageProps {
  icon: string
  title: string
}

export default function ComingSoonPage({ icon, title }: ComingSoonPageProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center py-20 text-center"
    >
      <span className="text-5xl mb-4">{icon}</span>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">{title}</h2>
      <p className="text-sm text-slate-400">此页面正在开发中...</p>
    </motion.div>
  )
}
