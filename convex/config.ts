import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Mutation to update the session token
export const updateSessionToken = mutation({
  args: {
    token: v.string(),
  },
  handler: async (ctx, args) => {
    // In a real app, you'd add authentication here
    // For now, we'll just validate the token format
    if (!args.token || args.token.length < 10) {
      throw new Error("Invalid token format");
    }
    
    // Store the token (you could also validate it's working)
    // For simplicity, we'll just return success
    // The actual file writing will be done via HTTP endpoint
    return { success: true, message: "Token update request received" };
  },
});

// Query to check if token file exists
export const getTokenStatus = query({
  handler: async (ctx) => {
    // This is just a placeholder - actual status would come from file system
    return { hasToken: true, source: "file" };
  },
}); 