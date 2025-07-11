import { v } from "convex/values";
import { defineSchema, defineTable } from "convex/server";

export default defineSchema({
  // Table to store the LATEST OHLCV bar for each stock
  ohlcv: defineTable({
    stock_code: v.string(),
    open: v.number(),
    high: v.number(),
    low: v.number(),
    close: v.number(),
    volume: v.number(),
    interval: v.string(),
    timestamp: v.number(), // Unix timestamp of the bar's start time
  }).index("by_stock_code", ["stock_code"]),
});