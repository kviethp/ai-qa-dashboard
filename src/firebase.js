import { initializeApp } from "firebase/app";
import { getDatabase, ref, onValue } from "firebase/database";

// Firebase configuration placeholder
// Anh Việt sẽ thay các thông số này bằng thông số từ Firebase Console
const firebaseConfig = {
  apiKey: "AIzaSyCJalVlctO_v4f2zlnimE962GySI2qJPkU",
  authDomain: "ai-qa-agents.firebaseapp.com",
  databaseURL: "https://ai-qa-agents-default-rtdb.firebaseio.com",
  projectId: "ai-qa-agents",
  storageBucket: "ai-qa-agents.firebasestorage.app",
  messagingSenderId: "305486207890",
  appId: "1:305486207890:web:3b4050cd99e8842f4eff4b",
  measurementId: "G-N149ZGHCYK"
};

let app, database;

// Kiểm tra xem config đã được điền chưa
const isConfigured = firebaseConfig.apiKey !== "YOUR_API_KEY";

if (isConfigured) {
  app = initializeApp(firebaseConfig);
  database = getDatabase(app);
}

export { database, ref, onValue, isConfigured };
