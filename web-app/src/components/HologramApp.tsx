"use client";

import React, { useEffect, useRef, useState } from "react";
import { HandLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { detectGesture, Landmark } from "@/lib/gestureUtils";
import styles from "./HologramApp.module.css";

interface HologramAppProps {
  onBack: () => void;
}

export default function HologramApp({ onBack }: HologramAppProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [handLandmarker, setHandLandmarker] = useState<HandLandmarker | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const requestRef = useRef<number>(0);
  const lastVideoTimeRef = useRef(-1);

  // Hologram transform state
  const rotX = useRef(0);
  const rotY = useRef(0);
  const scale = useRef(1);

  // Initialize MediaPipe
  useEffect(() => {
    async function initMediaPipe() {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
        );
        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "/models/hand_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.7,
          minHandPresenceConfidence: 0.7,
          minTrackingConfidence: 0.7
        });
        setHandLandmarker(landmarker);
      } catch (e) {
        console.error("Error loading MediaPipe", e);
      }
    }
    initMediaPipe();
  }, []);

  // Initialize Camera
  useEffect(() => {
    if (!handLandmarker) return;

    async function startCamera() {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error("Browser API navigator.mediaDevices.getUserMedia not available.");
        }
        
        if (videoRef.current) {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720 },
            audio: false,
          });
          videoRef.current.srcObject = stream;
          videoRef.current.addEventListener("loadeddata", () => {
            setIsLoading(false);
            predictWebcam();
          });
        }
      } catch (err: any) {
        console.error("Error accessing webcam:", err);
        setIsLoading(false);
      }
    }
    startCamera();

    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      // Stop camera streams
      if (videoRef.current?.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach(track => track.stop());
      }
    };
  }, [handLandmarker]);

  const predictWebcam = () => {
    if (!videoRef.current || !canvasRef.current || !handLandmarker) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Wait until video is fully loaded and has valid dimensions
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      requestRef.current = requestAnimationFrame(predictWebcam);
      return;
    }

    if (canvas.width !== video.videoWidth) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    const nowInMs = performance.now();

    if (video.currentTime !== lastVideoTimeRef.current) {
      lastVideoTimeRef.current = video.currentTime;
      const results = handLandmarker.detectForVideo(video, nowInMs);

      ctx.save();
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (results.landmarks && results.landmarks.length > 0) {
        const landmarks = results.landmarks[0];
        drawLandmarks(ctx, landmarks, canvas.width, canvas.height);

        // Calculate mapped coordinates
        const cw = window.innerWidth;
        const ch = window.innerHeight;
        
        // Mirror X
        const cx = (1 - landmarks[8].x) * cw;
        const cy = landmarks[8].y * ch;

        // Apply Holographic transforms
        // Rotates the object to directly face the hand
        const mappedRotY = ((cx / cw) - 0.5) * 180; // -90 to 90 degrees
        const mappedRotX = -((cy / ch) - 0.5) * 180; // -90 to 90 degrees

        rotY.current = mappedRotY;
        rotX.current = mappedRotX;

        // Estimate distance for scale using wrist to middle finger
        const dist = Math.sqrt(
          Math.pow(landmarks[0].x - landmarks[9].x, 2) + 
          Math.pow(landmarks[0].y - landmarks[9].y, 2)
        );
        // Dist is ~0.1 (far) to 0.4 (close)
        const mappedScale = Math.min(1.5, Math.max(0.5, dist * 4));
        scale.current = mappedScale;
        
      } else {
        // Slowly return to center when hand is lost
        rotX.current += (0 - rotX.current) * 0.1;
        rotY.current += (0 - rotY.current) * 0.1;
        scale.current += (1 - scale.current) * 0.1;
      }
      ctx.restore();
    }

    // Apply CSS transforms dynamically to avoid React render loop overhead
    const sceneEl = document.getElementById("hologram-scene");
    if (sceneEl) {
      sceneEl.style.transform = `rotateX(${rotX.current}deg) rotateY(${rotY.current}deg) scale(${scale.current})`;
    }

    requestRef.current = requestAnimationFrame(predictWebcam);
  };

  const drawLandmarks = (ctx: CanvasRenderingContext2D, landmarks: Landmark[], w: number, h: number) => {
    ctx.strokeStyle = "rgba(0, 230, 210, 0.4)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgba(0, 230, 210, 0.8)";

    const connections = [
      [0,1],[1,2],[2,3],[3,4],
      [0,5],[5,6],[6,7],[7,8],
      [5,9],[9,10],[10,11],[11,12],
      [9,13],[13,14],[14,15],[15,16],
      [13,17],[17,18],[18,19],[19,20],
      [0,17]
    ];

    connections.forEach(([i, j]) => {
      ctx.beginPath();
      ctx.moveTo(landmarks[i].x * w, landmarks[i].y * h);
      ctx.lineTo(landmarks[j].x * w, landmarks[j].y * h);
      ctx.stroke();
    });

    // Draw bright nodes
    landmarks.forEach((lm) => {
      ctx.beginPath();
      ctx.arc(lm.x * w, lm.y * h, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  };

  return (
    <div className={styles.container}>
      {isLoading && (
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <h2 style={{ color: '#00e6d2', fontWeight: 'bold', letterSpacing: '0.2em' }}>CALIBRATING HOLOGRAM</h2>
        </div>
      )}

      <button onClick={onBack} className={styles.backButton}>
        ← Exit Studio
      </button>

      <div className={styles.hints}>
        MOVE HAND TO ROTATE • BRING CLOSER TO SCALE
      </div>

      <video 
        ref={videoRef} 
        autoPlay 
        playsInline 
        muted 
        className={styles.videoFeed} 
      />

      <canvas 
        ref={canvasRef} 
        className={styles.skeletonCanvas} 
      />

      {/* Hologram Object */}
      {!isLoading && (
        <div id="hologram-scene" className={styles.hologramWrapper}>
          <div className={`${styles.cubeFace} ${styles.front}`}></div>
          <div className={`${styles.cubeFace} ${styles.back}`}></div>
          <div className={`${styles.cubeFace} ${styles.right}`}></div>
          <div className={`${styles.cubeFace} ${styles.left}`}></div>
          <div className={`${styles.cubeFace} ${styles.top}`}></div>
          <div className={`${styles.cubeFace} ${styles.bottom}`}></div>
          
          <div className={styles.core}>
            <div className={styles.coreRing}></div>
            <div className={styles.coreRing2}></div>
          </div>
        </div>
      )}
      
      {!isLoading && (
        <div className={styles.hudOverlay}>
          <div>SYS.STATUS: ONLINE</div>
          <div>OBJ.CLASS: TESSERACT_MOCK</div>
          <div>TRACKING: TRUE</div>
        </div>
      )}
    </div>
  );
}
