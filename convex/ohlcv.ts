import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Mutation to add or update the latest OHLCV bar for a stock.
// This is an "upsert" operation.
export const updateOhlcv = mutation({
  args: {
    stock_code: v.string(),
    open: v.number(),
    high: v.number(),
    low: v.number(),
    close: v.number(),
    volume: v.number(),
    interval: v.string(),
    timestamp: v.number(),
  },
  handler: async (ctx, args) => {
    // Look for an existing document for this stock_code using the index.
    const existing = await ctx.db
      .query("ohlcv")
      .withIndex("by_stock_code", (q) => q.eq("stock_code", args.stock_code))
      .unique();

    if (existing) {
      // If it exists, patch it with the new data. This is very efficient.
      await ctx.db.patch(existing._id, args);
    } else {
      // If it doesn't exist, insert a new document.
      await ctx.db.insert("ohlcv", args);
    }
  },
});

// Query to get all of the latest OHLCV bars for all stocks.
// The result is sorted by stock_code for a stable order in the UI.
export const get = query({
  handler: async (ctx) => {
    return await ctx.db.query("ohlcv").order("asc").collect();
  },
});