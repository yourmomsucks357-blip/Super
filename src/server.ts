import fastify from "fastify";
import cors from "@fastify/cors";
import { aiController } from "./routes/aiController";

const app = fastify({ logger: true });

app.register(cors);
app.register(aiController);

app.listen({ port: 3000, host: "0.0.0.0" }, (err, address) => {
  if (err) {
    app.log.error(err);
    process.exit(1);
  }
  app.log.info("Server listening on " + address);
});