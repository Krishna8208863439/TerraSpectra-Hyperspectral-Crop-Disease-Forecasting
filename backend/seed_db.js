import "dotenv/config";
import mongoose from "mongoose";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function seed() {
  const rawUri = process.env.MONGO_URI || process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/smart_kisan";
  const mongoUri = rawUri.includes("mongodb+srv://") ? rawUri : rawUri.replace("localhost", "127.0.0.1");

  console.log("Connecting to MongoDB for seeding...");
  await mongoose.connect(mongoUri, { serverSelectionTimeoutMS: 5000 });
  console.log(`Connected to database: ${mongoose.connection.name}`);

  const fallbackPath = path.join(__dirname, "db_fallback.json");
  if (!fs.existsSync(fallbackPath)) {
    console.error("db_fallback.json not found.");
    process.exit(1);
  }

  const fallbackData = JSON.parse(fs.readFileSync(fallbackPath, "utf-8"));

  for (const [collectionName, documents] of Object.entries(fallbackData)) {
    if (!Array.isArray(documents) || documents.length === 0) continue;

    const col = mongoose.connection.db.collection(collectionName);
    const existingCount = await col.countDocuments();

    if (existingCount === 0) {
      console.log(`Seeding '${collectionName}' with ${documents.length} sample records...`);
      // Convert string _id if needed or keep as is
      await col.insertMany(documents);
      console.log(`✓ Seeded '${collectionName}'`);
    } else {
      console.log(`- Collection '${collectionName}' already has ${existingCount} documents (skipping).`);
    }
  }

  console.log("\nSeeding check complete!");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seeding error:", err);
  process.exit(1);
});
