import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getDailyLearning } from '../api/client'
import type { LearningResponse } from '../types'
import MarkdownPreview from '../components/shared/MarkdownPreview'
import LoadingSkeleton from '../components/shared/LoadingSkeleton'

export default function LearningPage() {
  const [data, setData] = useState<LearningResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDailyLearning().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="max-w-3xl mx-auto"><LoadingSkeleton /></div>
  if (!data) return <div className="text-slate-400 text-sm">加载失败</div>

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-3xl mx-auto space-y-6">
      <div className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/30">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">📚</span>
          <div>
            <h2 className="text-lg font-semibold text-white">{data.topic}</h2>
            <p className="text-xs text-slate-400">{data.category} · {data.date}</p>
          </div>
        </div>
        <MarkdownPreview content={data.content} />
      </div>

      <div className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/30 border-l-blue-500 border-l-2">
        <h3 className="text-sm font-semibold text-slate-100 mb-4">教练提问</h3>
        <ol className="space-y-3">
          {data.questions.map((q, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
              <span className="text-blue-400 font-semibold w-5">{i + 1}.</span>
              {q}
            </li>
          ))}
        </ol>
        <p className="text-xs text-slate-400 mt-4">
          提示：学习效果 = 写下答案 &gt; 脑子里想过 &gt; 只看不写
        </p>
      </div>
    </motion.div>
  )
}
