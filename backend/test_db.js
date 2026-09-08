import "dotenv/config";
import mongoose from "mongoose";

const maskUri = (uri) => {
  if (!uri) return "(empty)";
  return uri.replace(/:\/\/([^:]+):([^@]+)@/, "://$1:****@");
};

async function testConnection() {
  console.log("========================================");
  console.log("       Smart Kisan MongoDB Tester       ");
  console.log("========================================");

  const rawUri = process.env.MONGO_URI || process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/smart_kisan";
  const mongoUri = rawUri.includes("mongodb+srv://") ? rawUri : rawUri.replace("localhost", "127.0.0.1");

  console.log(`Connecting to: ${maskUri(mongoUri)}`);

  const timeoutMs = parseInt(process.env.MONGO_TIMEOUT_MS, 10) || 5000;

  try {
    const startTime = Date.now();
    await mongoose.connect(mongoUri, {
      serverSelectionTimeoutMS: timeoutMs,
      connectTimeoutMS: timeoutMs,
    });
    const elapsed = Date.now() - startTime;

    console.log(`\n[SUCCESS] Connected to MongoDB in ${elapsed}ms!`);
    console.log(`Database Name : ${mongoose.connection.name}`);
    console.log(`Host          : ${mongoose.connection.host}`);
    console.log(`Port          : ${mongoose.connection.port || "default"}`);

    // Test ping
    const adminDb = mongoose.connection.db.admin();
    const pingResult = await adminDb.ping();
    console.log(`Ping Response : ${JSON.stringify(pingResult)}`);

    // List collections and counts
    const collections = await mongoose.connection.db.listCollections().toArray();
    console.log(`\nExisting Collections (${collections.length}):`);
    for (const col of collections) {
      const count = await mongoose.connection.db.collection(col.name).countDocuments();
      console.log(` - ${col.name.padEnd(20)}: ${count} documents`);
    }

    // Test Write & Read capability
    console.log("\nTesting Write/Read permissions...");
    const testCol = mongoose.connection.db.collection("__connectiontests");
    const testDoc = { test: true, timestamp: new Date() };
    const insertResult = await testCol.insertOne(testDoc);
    await testCol.deleteOne({ _id: insertResult.insertedId });
    console.log("[SUCCESS] Read/Write test passed cleanly!");

    console.log("\n========================================");
    console.log(" MongoDB is fully functional and ready! ");
    console.log("========================================\n");
    process.exit(0);
  } catch (error) {
    console.error(`\n[FAILED] MongoDB connection error: ${error.message}`);
    console.log("\nTroubleshooting tips:");
    if (mongoUri.includes("127.0.0.1") || mongoUri.includes("localhost")) {
      console.log("  1. Ensure local MongoDB service is running:");
      console.log("     Run in PowerShell (Admin): Start-Service MongoDB");
      console.log("     Or check in Services: 'MongoDB Server (MongoDB)' -> Running");
      console.log("  2. If using MongoDB Compass, connect to: mongodb://127.0.0.1:27017");
    } else if (mongoUri.includes("mongodb+srv://")) {
      console.log("  1. In MongoDB Atlas, go to 'Network Access' and whitelist your IP (or 0.0.0.0/0).");
      console.log("  2. In 'Database Access', verify username and password are correct.");
      console.log("  3. Check if your network/firewall blocks port 27017 or DNS SRV lookups.");
    }
    console.log("========================================\n");
    process.exit(1);
  }
}

testConnection();
