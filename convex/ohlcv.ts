import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Mutation to add or update the latest OHLCV bar for a stock.
// This is an "upsert" operation with better duplicate handling.
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
    // Look for existing documents for this stock_code using the index.
    const existingDocs = await ctx.db
      .query("ohlcv")
      .withIndex("by_stock_code", (q) => q.eq("stock_code", args.stock_code))
      .collect();

    if (existingDocs.length > 1) {
      // Clean up duplicates - keep the one with the latest timestamp and delete others
      const sortedDocs = existingDocs.sort((a, b) => b.timestamp - a.timestamp);
      const latestDoc = sortedDocs[0];
      
      // Delete duplicates
      for (let i = 1; i < sortedDocs.length; i++) {
        await ctx.db.delete(sortedDocs[i]._id);
      }
      
      // Update the latest document if the new data is newer
      if (args.timestamp > latestDoc.timestamp) {
        await ctx.db.patch(latestDoc._id, args);
      }
    } else if (existingDocs.length === 1) {
      const existing = existingDocs[0];
      // Only update if the new timestamp is newer or equal (to handle updates to the same bar)
      if (args.timestamp >= existing.timestamp) {
      await ctx.db.patch(existing._id, args);
      }
    } else {
      // If it doesn't exist, insert a new document.
      await ctx.db.insert("ohlcv", args);
    }
  },
});

// Query to get all realtime data, ordered by most recent updates
export const get = query({
  handler: async (ctx) => {
    return await ctx.db
      .query("ohlcv")
      .withIndex("by_stock_code") // Use index for better performance
      .order("desc")
      .collect();
  },
});

// Optional: Add a query to get only recently updated stocks
export const getRecent = query({
  args: { 
    minutesBack: v.optional(v.number()) 
  },
  handler: async (ctx, args) => {
    const minutesBack = args.minutesBack ?? 5;
    const cutoffTime = Math.floor(Date.now() / 1000) - (minutesBack * 60);
    
    return await ctx.db
      .query("ohlcv")
      .filter((q) => q.gte(q.field("timestamp"), cutoffTime))
      .order("desc")
      .collect();
  },
});

// Add a query to check for potential issues
export const getDuplicates = query({
  handler: async (ctx) => {
    const allDocs = await ctx.db.query("ohlcv").collect();
    const stockCounts = new Map<string, number>();
    
    for (const doc of allDocs) {
      stockCounts.set(doc.stock_code, (stockCounts.get(doc.stock_code) || 0) + 1);
    }
    
    const duplicates = Array.from(stockCounts.entries())
      .filter(([_, count]) => count > 1)
      .map(([stock_code, count]) => ({ stock_code, count }));
    
    return duplicates;
  },
});