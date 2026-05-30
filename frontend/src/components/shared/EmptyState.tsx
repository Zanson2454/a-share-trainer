interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ icon = '📭', title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <span className="text-4xl mb-4">{icon}</span>
      <h3 className="text-lg font-medium text-slate-100 mb-2">{title}</h3>
      {description && <p className="text-sm text-slate-400 max-w-md">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 bg-blue-500 text-slate-100 rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
