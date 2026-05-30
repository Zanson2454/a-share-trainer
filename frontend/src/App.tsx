import { Routes, Route } from 'react-router-dom'
import DashboardLayout from './components/layout/DashboardLayout'
import ErrorBoundary from './components/shared/ErrorBoundary'
import HomePage from './pages/HomePage'
import LearningPage from './pages/LearningPage'
import PremarketPage from './pages/PremarketPage'
import ScreeningPage from './pages/ScreeningPage'
import StockAnalysisPage from './pages/StockAnalysisPage'
import ReviewPage from './pages/ReviewPage'
import StrategyPage from './pages/StrategyPage'
import BacktestPage from './pages/BacktestPage'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/learning" element={<LearningPage />} />
          <Route path="/premarket" element={<PremarketPage />} />
          <Route path="/screening" element={<ScreeningPage />} />
          <Route path="/analysis" element={<StockAnalysisPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/strategies" element={<StrategyPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
