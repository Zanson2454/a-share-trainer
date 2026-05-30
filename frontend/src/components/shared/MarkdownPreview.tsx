import ReactMarkdown from 'react-markdown'

interface MarkdownPreviewProps {
  content: string
}

export default function MarkdownPreview({ content }: MarkdownPreviewProps) {
  return (
    <div className="prose prose-invert prose-sm max-w-none
      prose-headings:text-white
      prose-h2:text-lg prose-h2:font-semibold prose-h2:mt-6 prose-h2:mb-3
      prose-h3:text-base prose-h3:font-medium prose-h3:mt-4 prose-h3:mb-2
      prose-p:text-slate-300 prose-p:leading-relaxed
      prose-strong:text-white
      prose-table:text-sm
      prose-th:bg-slate-900 prose-th:px-3 prose-th:py-2 prose-th:text-slate-300
      prose-td:px-3 prose-td:py-2 prose-td:border-t prose-td:border-slate-700/30
      prose-li:text-slate-300
      prose-blockquote:border-l-blue-500 prose-blockquote:bg-slate-900 prose-blockquote:py-2 prose-blockquote:px-4 prose-blockquote:rounded-r
      prose-code:bg-slate-900 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
      prose-a:text-blue-400">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}
