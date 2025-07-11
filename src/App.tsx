import './App.css'
import { StockTickerTable } from './components/StockTickerTable'

function App() {
  return (
    <main>
      <h1>IndianRobinhood - Live Ticker</h1>
      <p>Displaying the latest 100 ticks from the ICICI Breeze API in real-time.</p>
      <StockTickerTable />
    </main>
  )
}

export default App

