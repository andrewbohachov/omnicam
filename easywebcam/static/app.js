// EasyWebcam WebRTC Client
const video = document.getElementById('preview');
const streamBtn = document.getElementById('stream-btn');
const btnLabel = document.getElementById('btn-label');
const statusBadge = document.getElementById('status-badge');
const statusText = document.getElementById('status-text');
const flipBtn = document.getElementById('flip-btn');
const torchBtn = document.getElementById('torch-btn');
const resSelect = document.getElementById('res-select');
const fpsSelect = document.getElementById('fps-select');
const statRes = document.getElementById('stat-res');
const statFps = document.getElementById('stat-fps');

let pc = null;
let localStream = null;
let currentFacingMode = 'environment'; // default to back camera
let isStreaming = false;
let wakeLock = null;
let torchOn = false;

const RESOLUTIONS = {
  '720': { width: 1280, height: 720 },
  '1080': { width: 1920, height: 1080 },
  '4k': { width: 3840, height: 2160 }
};

async function initCamera() {
  if (localStream) {
    localStream.getTracks().forEach(t => t.stop());
  }

  const resChoice = resSelect.value;
  const fpsChoice = parseInt(fpsSelect.value, 10);
  const target = RESOLUTIONS[resChoice] || RESOLUTIONS['1080'];

  statRes.textContent = `${resChoice}p`;
  statFps.textContent = `${fpsChoice} FPS`;

  const constraints = {
    audio: false, // STRICTLY NO AUDIO
    video: {
      facingMode: currentFacingMode,
      width: { ideal: target.width },
      height: { ideal: target.height },
      frameRate: { ideal: fpsChoice, min: 24, max: fpsChoice }
    }
  };

  try {
    localStream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = localStream;
    checkTorchSupport();
  } catch (err) {
    alert("Camera Access Error: " + err.message);
  }
}

function checkTorchSupport() {
  if (!localStream) return;
  const track = localStream.getVideoTracks()[0];
  const capabilities = track.getCapabilities ? track.getCapabilities() : {};
  if (capabilities.torch) {
    torchBtn.style.display = 'flex';
  } else {
    torchBtn.style.display = 'none';
  }
}

async function toggleTorch() {
  if (!localStream) return;
  const track = localStream.getVideoTracks()[0];
  torchOn = !torchOn;
  try {
    await track.applyConstraints({
      advanced: [{ torch: torchOn }]
    });
    torchBtn.style.background = torchOn ? '#f59e0b' : '';
  } catch (e) {
    console.error("Torch error", e);
  }
}

async function requestWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
    }
  } catch (err) {
    console.log("WakeLock error:", err);
  }
}

function releaseWakeLock() {
  if (wakeLock) {
    wakeLock.release();
    wakeLock = null;
  }
}

async function startStream() {
  if (!localStream) {
    await initCamera();
  }

  statusText.textContent = "CONNECTING...";
  
  // Clean WebRTC setup with LAN-only config
  pc = new RTCPeerConnection({ iceServers: [] });

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'connected') {
      statusText.textContent = "LIVE";
      statusBadge.classList.add('streaming');
      streamBtn.classList.add('active');
      btnLabel.textContent = "STOP STREAM";
      isStreaming = true;
      requestWakeLock();
    } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
      stopStream();
    }
  };

  const track = localStream.getVideoTracks()[0];
  const sender = pc.addTrack(track, localStream);

  // Tell browser's encoder: prioritize framerate, allocate high bitrate for local Wi-Fi
  try {
    const params = sender.getParameters();
    if (!params.encodings || params.encodings.length === 0) {
      params.encodings = [{}];
    }
    params.degradationPreference = 'maintain-framerate';
    const fpsChoice = parseInt(fpsSelect.value, 10);
    params.encodings[0].maxFramerate = fpsChoice;
    params.encodings[0].maxBitrate = 12000000; // 12 Mbps
    await sender.setParameters(params);
  } catch (e) {
    console.log("Sender parameters notice:", e);
  }

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  try {
    const res = await fetch('/offer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sdp: pc.localDescription.sdp,
        type: pc.localDescription.type
      })
    });

    if (!res.ok) throw new Error("Server error: " + res.status);
    const answer = await res.json();
    await pc.setRemoteDescription(new RTCSessionDescription(answer));
  } catch (err) {
    alert("Connection failed: " + err.message);
    stopStream();
  }
}

function stopStream() {
  if (pc) {
    pc.close();
    pc = null;
  }
  isStreaming = false;
  statusText.textContent = "READY";
  statusBadge.classList.remove('streaming');
  streamBtn.classList.remove('active');
  btnLabel.textContent = "START STREAM";
  releaseWakeLock();
}

// Event Listeners
streamBtn.addEventListener('click', () => {
  if (isStreaming) {
    stopStream();
  } else {
    startStream();
  }
});

flipBtn.addEventListener('click', async () => {
  currentFacingMode = currentFacingMode === 'environment' ? 'user' : 'environment';
  await initCamera();
  if (isStreaming) {
    stopStream();
    await startStream();
  }
});

torchBtn.addEventListener('click', toggleTorch);
resSelect.addEventListener('change', async () => {
  await initCamera();
  if (isStreaming) {
    stopStream();
    await startStream();
  }
});
fpsSelect.addEventListener('change', async () => {
  await initCamera();
  if (isStreaming) {
    stopStream();
    await startStream();
  }
});

window.addEventListener('DOMContentLoaded', () => {
  initCamera();
});
