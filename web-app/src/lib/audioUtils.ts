let audioCtx: AudioContext | null = null;

export function initAudio() {
  if (typeof window === "undefined") return;
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
}

export function playBeep(frequency = 440, type: OscillatorType = "sine", duration = 0.1) {
  if (!audioCtx) return;
  
  const oscillator = audioCtx.createOscillator();
  const gainNode = audioCtx.createGain();
  
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, audioCtx.currentTime);
  
  gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  
  oscillator.connect(gainNode);
  gainNode.connect(audioCtx.destination);
  
  oscillator.start();
  oscillator.stop(audioCtx.currentTime + duration);
}

export function playClickSound() {
  playBeep(800, "triangle", 0.05);
}

export function playToggleSound(isOn: boolean) {
  if (isOn) {
    playBeep(600, "sine", 0.1);
    setTimeout(() => playBeep(800, "sine", 0.15), 100);
  } else {
    playBeep(400, "sine", 0.15);
  }
}

export function playClearSound() {
  playBeep(200, "square", 0.2);
}

export function playErrorSound() {
  playBeep(150, "sawtooth", 0.3);
}
