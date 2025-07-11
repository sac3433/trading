import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const http = httpRouter();

// Define an HTTP endpoint to receive OHLCV bars from our Python service
http.route({
  path: "/ingestOhlcv",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const bar = await request.json();

    // Add the OHLCV bar to the database using our new mutation
    await ctx.runMutation(api.ohlcv.updateOhlcv, bar);

    return new Response(null, { status: 200 });
  }),
});

export default http;