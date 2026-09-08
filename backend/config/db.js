import mongoose from "mongoose";

global.useMemoryDB = false;

// Register connection lifecycle listeners once
mongoose.connection.on("error", (err) => {
  console.error(`[MongoDB] Runtime connection error: ${err.message}`);
});

mongoose.connection.on("disconnected", () => {
  console.warn("[MongoDB] Connection lost.");
});

mongoose.connection.on("reconnected", () => {
  console.log("[MongoDB] Reconnected successfully.");
});

export const connectDB = async () => {
  try {
    const rawUri = process.env.MONGO_URI || process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/smart_kisan";
    // If local localhost, use 127.0.0.1 to prevent IPv6/IPv4 resolution delay on Node 18+
    const mongoUri = rawUri.includes("mongodb+srv://") ? rawUri : rawUri.replace("localhost", "127.0.0.1");

    const timeoutMs = parseInt(process.env.MONGO_TIMEOUT_MS, 10) || 5000;

    await mongoose.connect(mongoUri, {
      serverSelectionTimeoutMS: timeoutMs,
      connectTimeoutMS: timeoutMs,
    });

    global.useMemoryDB = false;
    const dbName = mongoose.connection.name || "smart_kisan";
    const host = mongoose.connection.host || "127.0.0.1";
    console.log(`✅ MongoDB connected successfully to [${dbName}] at ${host}`);
  } catch (err) {
    console.warn(`⚠️ MongoDB connection failed: ${err.message}`);
    console.warn("   Falling back to local file-based database (db_fallback.json)...");
    global.useMemoryDB = true;
  }
};

