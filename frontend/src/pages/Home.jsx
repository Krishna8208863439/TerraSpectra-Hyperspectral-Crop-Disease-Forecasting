import React from "react";
import { Link } from "react-router-dom";
import { 
  Camera, 
  CloudRain, 
  TrendingUp, 
  MessageSquare, 
  ArrowRight, 
  Sparkles, 
  Phone,
  ShieldCheck
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import "./Home.css";

export default function Home() {
  const { user } = useAuth();
  const { language } = useLanguage();
  const isMr = language === "mr";

  return (
    <div className="simple-home">
      {/* ── CLEAN HERO ── */}
      <section className="simple-hero">
        <div className="simple-hero-badge">
          <Sparkles size={15} />
          <span>{isMr ? "स्मार्ट किसान • डिजिटल कृषी साथी" : "Smart Kisan • Digital Agriculture"}</span>
        </div>

        <h1 className="simple-hero-title">
          {isMr ? (
            <>
              शेती झाली सोपी,<br />
              <span className="simple-hero-highlight">उत्पादन व नफा दुप्पट.</span>
            </>
          ) : (
            <>
              Farming Made Simpler,<br />
              <span className="simple-hero-highlight">Smarter & More Profitable.</span>
            </>
          )}
        </h1>

        <p className="simple-hero-desc">
          {isMr
            ? "मोबाईल कॅमेऱ्याने पिकांचे आजार ओळखा, अचूक औषध फवारणी सल्ला मिळवा, रोजचे बाजारभाव तपासा आणि पावसाचा ७ दिवसांचा अंदाज घ्या — सर्वकाही १००% मोफत."
            : "Diagnose crop leaf diseases with your camera, get instant medicine advice, compare live APMC Mandi rates, and check 7-day village rain forecasts — 100% free."}
        </p>

        <div className="simple-hero-actions">
          {user ? (
            <Link to="/dashboard" className="simple-btn-primary">
              <span>{isMr ? "माझा डॅशबोर्ड उघडा 🚜" : "Open Dashboard 🚜"}</span>
              <ArrowRight size={18} />
            </Link>
          ) : (
            <>
              <Link to="/register" className="simple-btn-primary">
                <span>{isMr ? "मोफत नोंदणी करा 🚀" : "Get Started Free 🚀"}</span>
                <ArrowRight size={18} />
              </Link>
              <Link to="/login" className="simple-btn-secondary">
                <span>{isMr ? "लॉगिन करा 🔑" : "Farmer Login 🔑"}</span>
              </Link>
            </>
          )}
        </div>
      </section>

      {/* ── 4 CORE ESSENTIAL FEATURES ── */}
      <section>
        <div className="simple-features-header">
          <h2 className="simple-features-title">
            {isMr ? "मुख्य शेती साधने" : "Essential Farming Tools"}
          </h2>
          <p className="simple-features-sub">
            {isMr ? "खालील पर्यायांपैकी एक निवडा आणि लगेच वापरा:" : "Select any tool below to get started immediately:"}
          </p>
        </div>

        <div className="simple-cards-grid" style={{ marginTop: 20 }}>
          {/* Card 1: Plant Doctor */}
          <Link to="/ai-tools" className="simple-card">
            <div className="simple-card-icon" style={{ background: "rgba(34, 197, 94, 0.12)", color: "#16a34a" }}>
              <Camera size={26} />
            </div>
            <h3 className="simple-card-title">
              {isMr ? "पिकांचे डॉक्टर (AI Scan)" : "Crop Leaf Doctor"}
            </h3>
            <p className="simple-card-desc">
              {isMr
                ? "बाधित पानाचा फोटो काढा. ३ सेकंदात आजाराचे नाव व योग्य औषध फवारणी प्रमाण मिळवा."
                : "Snap a photo of sick leaves. Get instant disease diagnosis and exact spray medicine dosage."}
            </p>
            <div className="simple-card-action">
              <span>{isMr ? "पान स्कॅन करा" : "Scan Leaf"}</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Card 2: Weather */}
          <Link to="/weather" className="simple-card">
            <div className="simple-card-icon" style={{ background: "rgba(2, 132, 199, 0.12)", color: "#0284c7" }}>
              <CloudRain size={26} />
            </div>
            <h3 className="simple-card-title">
              {isMr ? "हवामान व पाऊस अंदाज" : "Village Rain & Weather"}
            </h3>
            <p className="simple-card-desc">
              {isMr
                ? "गावातील ७ दिवसांचा अचूक पाऊस अंदाज व फवारणीसाठी वाऱ्याचा वेग तपासा."
                : "7-day rain forecast and wind speeds to schedule your irrigation and spraying safely."}
            </p>
            <div className="simple-card-action">
              <span>{isMr ? "हवामान पहा" : "Check Weather"}</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Card 3: Mandi Rates */}
          <Link to="/market" className="simple-card">
            <div className="simple-card-icon" style={{ background: "rgba(217, 119, 6, 0.12)", color: "#d97706" }}>
              <TrendingUp size={26} />
            </div>
            <h3 className="simple-card-title">
              {isMr ? "APMC बाजारभाव" : "Live Mandi Rates"}
            </h3>
            <p className="simple-card-desc">
              {isMr
                ? "कांदा, गहू, कापूस, टोमॅटोचे आजचे बाजारभाव तपासा आणि जास्त नफा मिळवा."
                : "Track today's market rates for all crops across nearby APMC mandis before selling."}
            </p>
            <div className="simple-card-action">
              <span>{isMr ? "भाव तपासा" : "View Rates"}</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Card 4: Kisan AI Chat */}
          <Link to="/chat" className="simple-card">
            <div className="simple-card-icon" style={{ background: "rgba(139, 92, 246, 0.12)", color: "#8b5cf6" }}>
              <MessageSquare size={26} />
            </div>
            <h3 className="simple-card-title">
              {isMr ? "किसान AI सल्लागार" : "AgriExpert AI Chat"}
            </h3>
            <p className="simple-card-desc">
              {isMr
                ? "मराठी किंवा इंग्रजीत खते, पाणी किंवा किडींबद्दल कधीही २४ तास प्रश्न विचारा."
                : "Chat 24/7 in your language. Ask any question on fertilizer doses, pests, or crops."}
            </p>
            <div className="simple-card-action">
              <span>{isMr ? "प्रश्न विचारा" : "Ask Question"}</span>
              <ArrowRight size={16} />
            </div>
          </Link>
        </div>
      </section>

      {/* ── SIMPLE FOOTER HELPLINE ── */}
      <div className="simple-footer-banner">
        <div className="simple-helpline">
          <Phone size={18} color="#16a34a" />
          <span>
            {isMr ? "किसान कॉल सेंटर मोफत हेल्पलाइन: " : "Kisan Call Centre Toll-Free: "}
            <strong>1800-180-1551</strong>
          </span>
        </div>

        <div className="simple-footer-note">
          © {new Date().getFullYear()} Smart Kisan • {isMr ? "भारतीय शेतकऱ्यांसाठी समर्पित" : "Dedicated to Indian Agriculture"}
        </div>
      </div>
    </div>
  );
}
