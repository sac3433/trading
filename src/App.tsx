import './App.css'
import { StockTickerTable } from './components/StockTickerTable'
import { TokenManager } from "./components/TokenManager";

function App() {
  return (
    <main>
      <h1>Indianrobinhood - Real-time NSE Stock Data</h1>
      <TokenManager />
      <StockTickerTable />
    </main>
  );
}

export default App

