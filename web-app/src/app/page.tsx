"use client";

import React, { useState } from "react";
import GestureApp from "@/components/GestureApp";
import HologramApp from "@/components/HologramApp";
import { ArrowRight, Monitor, Sparkles, Cpu, Layers } from "lucide-react";
import styles from "./page.module.css";

export default function Home() {
  const [view, setView] = useState<"home" | "options" | "app" | "hologram">("home");

  if (view === "app") {
    return <GestureApp onBack={() => setView("options")} />;
  }
  if (view === "hologram") {
    return <HologramApp onBack={() => setView("options")} />;
  }

  return (
    <main className={styles.mainContainer}>
      {/* Dynamic Background Elements */}
      <div className={styles.bgGlowContainer}>
        <div className={`${styles.glowOrb} ${styles.glowTeal}`}></div>
        <div className={`${styles.glowOrb} ${styles.glowPurple}`}></div>
        <div className={`${styles.glowOrb} ${styles.glowOrange}`}></div>
      </div>

      <div className={styles.contentWrapper}>
        {view === "home" && (
          <div className={`${styles.viewSection} ${styles.fadeInUp}`}>
            <div className={styles.badge}>
              <Sparkles className={styles.badgeIcon} />
              <span>NEXT-GEN INTERACTION MODEL</span>
            </div>
            
            <h1 className={styles.heroTitle}>
              Touch the <br /> 
              <span className={styles.heroTitleHighlight}>
                Intangible.
              </span>
            </h1>
            
            <p className={styles.heroSubtitle}>
              Experience the future of digital workspaces. Control, draw, and interact using highly precise, AI-powered hand tracking. No hardware required.
            </p>
            
            <div className={styles.buttonWrapper}>
              <div className={styles.buttonGlow}></div>
              <button
                onClick={() => setView("options")}
                className={styles.primaryButton}
              >
                <span>Let's Begin</span>
                <ArrowRight className={styles.btnIcon} />
              </button>
            </div>
          </div>
        )}

        {view === "options" && (
          <div className={`${styles.viewSection} ${styles.fadeIn}`}>
            <h2 className={styles.sectionTitle}>
              Select Your Workspace
            </h2>
            <p className={styles.sectionSubtitle}>
              Choose an interactive environment to launch your camera-powered gesture experience.
            </p>
            
            <div className={styles.cardsGrid}>
              {/* Option 1: Smart Board */}
              <button
                onClick={() => setView("app")}
                className={`${styles.card} ${styles.cardActive}`}
              >
                <div className={styles.cardGlow}></div>
                <div className={`${styles.cardIconWrapper} ${styles.iconTeal}`}>
                  <Monitor className={styles.cardIcon} />
                </div>
                <h3 className={styles.cardTitle}>Smart Board</h3>
                <p className={styles.cardDesc}>
                  A gesture-controlled digital canvas. Draw, erase, and interact with extreme precision using just your hand movements in real-time.
                </p>
                <div className={styles.cardAction}>
                  Launch Space <ArrowRight className={styles.cardActionIcon} />
                </div>
              </button>

              {/* Option 2: Hologram Studio */}
              <button
                onClick={() => setView("hologram")}
                className={`${styles.card} ${styles.cardActive}`}
              >
                <div className={styles.cardGlow}></div>
                <div className={`${styles.cardIconWrapper} ${styles.iconPurple}`}>
                  <Layers className={styles.cardIcon} />
                </div>
                <h3 className={styles.cardTitle}>Hologram Studio</h3>
                <p className={styles.cardDesc}>
                  Manipulate 3D holograms in physical space. Rotate, scale, and inspect glowing geometric structures using hand gestures.
                </p>
                <div className={styles.cardAction}>
                  Launch Space <ArrowRight className={styles.cardActionIcon} />
                </div>
              </button>

              {/* Option 3: Logic Gates (Placeholder) */}
              <button className={`${styles.card} ${styles.cardDisabled}`}>
                <div className={`${styles.cardIconWrapper} ${styles.iconGray}`}>
                  <Cpu className={styles.cardIcon} />
                </div>
                <h3 className={styles.cardTitle}>Logic Node</h3>
                <p className={styles.cardDesc}>
                  Visual node-based programming. Connect logic gates and build computational circuits dynamically with pinch gestures.
                </p>
                <div className={styles.cardBadge}>Coming Soon</div>
              </button>
            </div>
            
            <div className={styles.backWrapper}>
              <button 
                onClick={() => setView("home")}
                className={styles.backButton}
              >
                ← Back to Home
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
