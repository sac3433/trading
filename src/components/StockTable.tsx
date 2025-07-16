import type { Doc } from "../../convex/_generated/dataModel";

type SortConfig = {
  key: keyof Doc<"ohlcv">;
  direction: "ascending" | "descending";
} | null;

type StockTableProps = {
  bars: Doc<"ohlcv">[];
  updatedRows: Record<string, "up" | "down" | undefined>;
  requestSort: (key: keyof Doc<"ohlcv">) => void;
  sortConfig: SortConfig;
  onAnimationEnd: (id: string) => void;
};

const getSortIndicator = (key: keyof Doc<"ohlcv">, sortConfig: SortConfig) => {
  if (!sortConfig || sortConfig.key !== key) {
    return null;
  }
  return sortConfig.direction === "ascending" ? " ▲" : " ▼";
};

const formatTimestamp = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' });
};

const formatCurrency = (value: number) => {
  return value.toFixed(2);
};

const headers: { key: keyof Doc<"ohlcv">; label: string }[] = [
  { key: "stock_code", label: "Stock Code" },
  { key: "open", label: "Open" },
  { key: "high", label: "High" },
  { key: "low", label: "Low" },
  { key: "close", label: "Close" },
  { key: "volume", label: "Volume" },
  { key: "timestamp", label: "Last Update" },
];

export function StockTable({ bars, updatedRows, requestSort, sortConfig, onAnimationEnd }: StockTableProps) {
  return (
    <table>
      <thead>
        <tr>
          {headers.map(({ key, label }) => (
            <th key={key} onClick={() => requestSort(key)} className="sortable">
              {label}
              {getSortIndicator(key, sortConfig)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {bars.map((bar) => (
          <tr
            key={bar._id}
            className={updatedRows[bar._id] === 'up' ? 'flash-up' : updatedRows[bar._id] === 'down' ? 'flash-down' : ''}
            onAnimationEnd={() => onAnimationEnd(bar._id)}
          >
            <td>{bar.stock_code}</td>
            <td>{formatCurrency(bar.open)}</td>
            <td>{formatCurrency(bar.high)}</td>
            <td>{formatCurrency(bar.low)}</td>
            <td>{formatCurrency(bar.close)}</td>
            <td>{bar.volume}</td>
            <td>{formatTimestamp(bar.timestamp)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}