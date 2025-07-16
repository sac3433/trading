import { useState, useEffect, useMemo } from "react";
import { useQuery } from "convex/react";
import type { Doc } from "../../convex/_generated/dataModel";
import { api } from "../../convex/_generated/api";
import { usePrevious, useDebounce } from "../hooks";
import { StockTable } from "./StockTable";

export function StockTickerTable() {
  // Hook 1: useQuery
  const ohlcvBars = useQuery(api.ohlcv.get);
  // Hook 2: usePrevious
  const prevOhlcvBars = usePrevious(ohlcvBars);
  // Hook 3: useState
  const [searchTerm, setSearchTerm] = useState("");
  // Hook 4: useDebounce
  const debouncedSearchTerm = useDebounce(searchTerm, 300); // Debounce input by 300ms
  // Hook 5: useState
  const [updatedRows, setUpdatedRows] = useState<Record<string, "up" | "down" | undefined>>({});
  // Hook 6: useState
  const [sortConfig, setSortConfig] = useState<{
    key: keyof Doc<"ohlcv">;
    direction: "ascending" | "descending";
  } | null>({ key: "stock_code", direction: "ascending" });

  // Hook 7: useEffect
  useEffect(() => {
    if (!prevOhlcvBars || !ohlcvBars) return;

    const newUpdates: Record<string, "up" | "down"> = {};
    const prevBarsMap = new Map(prevOhlcvBars.map(bar => [bar._id, bar]));

    for (const newBar of ohlcvBars) {
      const prevBar = prevBarsMap.get(newBar._id);
      if (prevBar && newBar.close !== prevBar.close) {
        newUpdates[newBar._id] = newBar.close > prevBar.close ? "up" : "down";
      }
    }
    
    if (Object.keys(newUpdates).length > 0) {
      setUpdatedRows((prev) => ({ ...prev, ...newUpdates }));
    }
  }, [ohlcvBars, prevOhlcvBars]);

  // Hook 8: useMemo - MOVED TO THE TOP LEVEL
  const processedBars = useMemo(() => {
    if (!ohlcvBars) return [];

    let items = ohlcvBars.filter((bar) =>
      bar.stock_code.toLowerCase().includes(debouncedSearchTerm.toLowerCase())
    );

    if (sortConfig !== null) {
      items.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === "ascending" ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === "ascending" ? 1 : -1;
        }
        return 0;
      });
    }
    return items;
  }, [ohlcvBars, sortConfig, debouncedSearchTerm]);

  // Conditional returns are now safe because all hooks have been called
  if (ohlcvBars === undefined) {
    return <div>Loading real-time data...</div>;
  }

  if (ohlcvBars.length === 0) {
    return (
      <div>
        <h2>Waiting for data...</h2>
        <p>The data ingestor might be waiting for the market to open.</p>
      </div>
    );
  }

  const requestSort = (key: keyof Doc<"ohlcv">) => {
    let direction: "ascending" | "descending" = "ascending";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "ascending") {
      direction = "descending";
    }
    setSortConfig({ key, direction });
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Search by stock code..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        style={{ marginBottom: '1rem', padding: '0.5rem', width: '300px' }}
      />
      <StockTable
        bars={processedBars}
        updatedRows={updatedRows}
        requestSort={requestSort}
        sortConfig={sortConfig}
        onAnimationEnd={(id) =>
          setUpdatedRows((prev) => ({ ...prev, [id]: undefined }))
        }
      />
    </div>
  );
}
