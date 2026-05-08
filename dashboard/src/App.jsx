import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/layout/AppShell';

// Pages
import Overview from './pages/Overview';
import Portfolio from './pages/Portfolio';
import Scanner from './pages/Scanner';
import Risk from './pages/Risk';
import Backtest from './pages/Backtest';
import Settings from './pages/Settings';

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
          <Route path="backtest" element={<Backtest />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
