import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/layout/AppShell';

// Pages
import Overview from './pages/Overview';
import Portfolio from './pages/Portfolio';
import Scanner from './pages/Scanner';
import Risk from './pages/Risk';
import Backtest from './pages/Backtest';
import Settings from './pages/Settings';
import LiveScanner from './pages/LiveScanner';
import EveningScanner from './pages/EveningScanner';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/portfolio" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="scanner" element={<Scanner />} />
          <Route path="risk" element={<Risk />} />
          <Route path="live" element={<LiveScanner />} />
          <Route path="evening" element={<EveningScanner />} />
          <Route path="backtest" element={<Backtest />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
