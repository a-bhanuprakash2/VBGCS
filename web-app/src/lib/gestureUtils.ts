export type Landmark = { x: number; y: number; z: number };

export function distance(p1: Landmark, p2: Landmark) {
  return Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2));
}

// MediaPipe landmarks:
// 0: WRIST, 4: THUMB_TIP, 8: INDEX_TIP, 12: MIDDLE_TIP, 16: RING_TIP, 20: PINKY_TIP
// 5, 9, 13, 17 are the MCP (knuckles)

export function isFingerUp(tipIdx: number, pipIdx: number, landmarks: Landmark[]) {
  const wrist = landmarks[0];
  const tipDist = distance(wrist, landmarks[tipIdx]);
  const pipDist = distance(wrist, landmarks[pipIdx]);
  return tipDist > pipDist;
}

export function detectGesture(landmarks: Landmark[]) {
  if (!landmarks || landmarks.length < 21) return { name: "—", action: "none" };

  // Use PIP joints for better accuracy
  const indexUp = isFingerUp(8, 6, landmarks);
  const middleUp = isFingerUp(12, 10, landmarks);
  const ringUp = isFingerUp(16, 14, landmarks);
  const pinkyUp = isFingerUp(20, 18, landmarks);

  // Pinch is distance between Thumb Tip (4) and Index Tip (8)
  const indexThumbDist = distance(landmarks[4], landmarks[8]);
  const isPinching = indexThumbDist < 0.08;

  // 1. Pinch has highest priority (Click / Color)
  if (isPinching) {
    return { name: "👌 Pinch (Click/Color)", action: "pinch" };
  }

  // 2. Open Palm (Erase)
  if (indexUp && middleUp && ringUp && pinkyUp) {
    return { name: "🖐 Open Palm (Erase/Settings)", action: "palm" };
  }

  // 3. Fist (Clear)
  if (!indexUp && !middleUp && !ringUp && !pinkyUp) {
    return { name: "✊ Fist (Clear/Explorer)", action: "fist" };
  }

  // 4. Peace Sign (Toggle Board)
  if (indexUp && middleUp && !ringUp && !pinkyUp) {
    return { name: "✌ Peace (Toggle Board)", action: "peace" };
  }

  // 5. Index Only (Move/Draw)
  if (indexUp && !middleUp && !ringUp && !pinkyUp) {
    return { name: "☝ Index (Move/Draw)", action: "index" };
  }

  return { name: "—", action: "none" };
}
