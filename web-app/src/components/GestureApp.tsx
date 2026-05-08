"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { HandLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { detectGesture, Landmark } from "@/lib/gestureUtils";
import { initAudio, playClickSound, playClearSound } from "@/lib/audioUtils";
import { Trash2, Download, Undo, Palette, X } from "lucide-react";
import styles from "./GestureApp.module.css";

const COLORS = ["#00e6d2", "#ff9600", "#b43cdc", "#3cdc50", "#e6e6e6"];
const MAX_HISTORY = 15;

interface GestureAppProps {
  onBack: () => void;
}

export default function GestureApp({ onBack }: GestureAppProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const boardRef = useRef<HTMLCanvasElement>(null);

  const [handLandmarker, setHandLandmarker] = useState<HandLandmarker | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [colorIndex, setColorIndex] = useState(0);
  const colorIndexRef = useRef(0);

  useEffect(() => {
    colorIndexRef.current = colorIndex;
  }, [colorIndex]);

  const [brushSize, setBrushSize] = useState(5);
  const [showPalette, setShowPalette] = useState(false);
  
  // Undo history stack
  const historyRef = useRef<ImageData[]>([]);

  const requestRef = useRef<number>(0);
  const lastVideoTimeRef = useRef(-1);

  // Drawing state
  const isDrawing = useRef(false);
  const lastDrawPos = useRef({ x: 0, y: 0 });
  const lastActionTime = useRef(0);

  // Initialize MediaPipe and Camera
  useEffect(() => {
    initAudio(); 

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
        console.error(e);
      }
    }
    initMediaPipe();
  }, []);

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
    };
  }, [handLandmarker]);

  const saveHistorySnapshot = () => {
    if (!boardRef.current) return;
    const ctx = boardRef.current.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    const snapshot = ctx.getImageData(0, 0, boardRef.current.width, boardRef.current.height);
    historyRef.current.push(snapshot);
    if (historyRef.current.length > MAX_HISTORY) {
      historyRef.current.shift();
    }
  };

  const undoLastStroke = () => {
    if (!boardRef.current || historyRef.current.length === 0) return;
    playClickSound();
    const ctx = boardRef.current.getContext("2d");
    if (!ctx) return;
    const previousSnapshot = historyRef.current.pop();
    if (previousSnapshot) {
      ctx.putImageData(previousSnapshot, 0, 0);
    }
  };

  const saveCanvasAsImage = () => {
    if (!boardRef.current) return;
    playClickSound();
    const dataUrl = boardRef.current.toDataURL("image/png");
    const link = document.createElement("a");
    link.download = `SmartBoard_Sketch_${new Date().getTime()}.png`;
    link.href = dataUrl;
    link.click();
  };

  const clearBoard = () => {
    if (!boardRef.current) return;
    playClearSound();
    saveHistorySnapshot();
    const ctx = boardRef.current.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, boardRef.current.width, boardRef.current.height);
  };

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

        // Map gesture coordinates to the entire screen
        const cw = window.innerWidth;
        const ch = window.innerHeight;
        const nx = landmarks[8].x;
        const ny = landmarks[8].y;

        // Mirror X
        const cx = (1 - nx) * cw;
        const cy = ny * ch;

        processGesture(landmarks, cx, cy);
      } else {
        if (isDrawing.current) {
          isDrawing.current = false;
          saveHistorySnapshot();
        }
      }
      ctx.restore();
    }

    requestRef.current = requestAnimationFrame(predictWebcam);
  };

  const drawLandmarks = (ctx: CanvasRenderingContext2D, landmarks: Landmark[], w: number, h: number) => {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgba(0, 230, 210, 0.6)";

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

    // Draw index fingertip brighter
    ctx.beginPath();
    ctx.arc(landmarks[8].x * w, landmarks[8].y * h, 6, 0, 2 * Math.PI);
    ctx.fillStyle = COLORS[colorIndexRef.current];
    ctx.shadowColor = COLORS[colorIndexRef.current];
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
  };

  const processGesture = (landmarks: Landmark[], cx: number, cy: number) => {
    const gesture = detectGesture(landmarks);
    const now = performance.now();
    const canToggle = now - lastActionTime.current > 1000;

    if (gesture.action === "fist" && canToggle) {
      clearBoard();
      lastActionTime.current = now;
      isDrawing.current = false;
    } else if (gesture.action === "palm") {
      eraseBoard(cx, cy);
      isDrawing.current = false;
    } else if (gesture.action === "index") {
      drawOnBoard(cx, cy);
    } else {
      if (isDrawing.current) {
        saveHistorySnapshot();
        isDrawing.current = false;
      }
    }
  };

  const drawOnBoard = (x: number, y: number) => {
    if (!boardRef.current) return;
    
    const parent = boardRef.current.parentElement;
    if (parent && (boardRef.current.width !== parent.clientWidth || boardRef.current.height !== parent.clientHeight)) {
      boardRef.current.width = parent.clientWidth;
      boardRef.current.height = parent.clientHeight;
    }
    
    const ctx = boardRef.current.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    if (!isDrawing.current) {
      saveHistorySnapshot();
      lastDrawPos.current = { x, y };
      isDrawing.current = true;
    }

    const lastBx = lastDrawPos.current.x;
    const lastBy = lastDrawPos.current.y;

    ctx.beginPath();
    ctx.moveTo(lastBx, lastBy);
    ctx.lineTo(x, y);
    ctx.strokeStyle = COLORS[colorIndexRef.current];
    ctx.lineWidth = brushSize;
    ctx.lineCap = "round";
    ctx.stroke();

    lastDrawPos.current = { x, y };
  };

  const eraseBoard = (x: number, y: number) => {
    if (!boardRef.current) return;
    const ctx = boardRef.current.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    ctx.clearRect(x - 40, y - 40, 80, 80);
  };

  useEffect(() => {
    const resizeBoard = () => {
      if (boardRef.current) {
        boardRef.current.width = window.innerWidth;
        boardRef.current.height = window.innerHeight;
      }
    };
    
    setTimeout(resizeBoard, 500);
    window.addEventListener("resize", resizeBoard);
    return () => window.removeEventListener("resize", resizeBoard);
  }, []);

  return (
    <div className={styles.container}>
      
      {/* Loading State */}
      {isLoading && (
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <h2 className={styles.loadingTitle}>INITIALIZING AI TRACKING</h2>
          <p className={styles.loadingSub}>Please allow camera access</p>
        </div>
      )}

      <button onClick={onBack} className={styles.backButton}>
        ← Exit Board
      </button>

      {/* 
        Video Feed: 
        Mirrored, heavily blurred and low opacity, blending into the black background. 
        This provides the "my hand should trace in the background" effect while keeping the board dark and clean.
      */}
      <video 
        ref={videoRef} 
        autoPlay 
        playsInline 
        muted 
        className={styles.videoFeed} 
      />

      {/* The main Smart Board Canvas */}
      <canvas 
        ref={boardRef} 
        className={styles.boardCanvas} 
      />

      {/* Hand Skeleton Overlay */}
      <canvas 
        ref={canvasRef} 
        className={styles.skeletonCanvas} 
      />

      {/* Ultra Premium Floating Dock */}
      {!isLoading && (
        <div className={styles.dock}>
          
          <button 
            onClick={undoLastStroke}
            className={styles.dockButton}
            title="Undo (or gesture)"
          >
            <Undo size={20} />
          </button>
          
          <div className={styles.dockDivider}></div>

          <button 
            onClick={() => setShowPalette(!showPalette)}
            className={`${styles.dockButton} ${showPalette ? styles.active : ''}`}
          >
            <Palette size={20} />
            <span className={styles.colorBadge} style={{ backgroundColor: COLORS[colorIndex] }}></span>
          </button>

          <div className={styles.dockDivider}></div>

          <button 
            onClick={clearBoard}
            className={`${styles.dockButton} ${styles.danger}`}
            title="Clear Board (Fist gesture)"
          >
            <Trash2 size={20} />
          </button>

          <button 
            onClick={saveCanvasAsImage}
            className={`${styles.dockButton} ${styles.primary}`}
            title="Download Sketch"
          >
            <Download size={20} />
          </button>

          {/* Color Palette Popover */}
          {showPalette && (
            <div className={styles.palettePopup}>
              {COLORS.map((color, i) => (
                <button
                  key={color}
                  onClick={() => {
                    setColorIndex(i);
                    setShowPalette(false);
                  }}
                  className={`${styles.colorOption} ${colorIndex === i ? styles.colorOptionActive : ''}`}
                  style={{ backgroundColor: color, borderColor: colorIndex === i ? 'white' : 'transparent', boxShadow: colorIndex === i ? `0 0 15px ${color}` : 'none' }}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Subtle Instructions */}
      {!isLoading && (
        <div className={styles.hints}>
          <span>☝️ DRAW</span>
          <span>✋ ERASE</span>
          <span>✊ CLEAR</span>
        </div>
      )}
      
    </div>
  );
}
