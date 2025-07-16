import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const http = httpRouter();

// Define an HTTP endpoint to receive OHLCV bars from our Python service
http.route({
  path: "/ingestOhlcv",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
    const bar = await request.json();

      // Validate the incoming data
      if (!bar.stock_code || typeof bar.timestamp !== 'number') {
        console.error("Invalid bar data received:", bar);
        return new Response("Invalid data format", { status: 400 });
      }
      
      console.log(`Received bar for ${bar.stock_code} at timestamp ${bar.timestamp} (${new Date(bar.timestamp * 1000).toISOString()})`);

      // Add the OHLCV bar to the database using our improved mutation
    await ctx.runMutation(api.ohlcv.updateOhlcv, bar);
      
      console.log(`Successfully processed bar for ${bar.stock_code}`);

    return new Response(null, { status: 200 });
    } catch (error) {
      console.error("Error processing OHLCV bar:", error);
      return new Response("Internal server error", { status: 500 });
    }
  }),
});

export default http;