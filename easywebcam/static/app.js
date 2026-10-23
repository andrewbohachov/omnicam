// EasyWebcam WebRTC Client with Bidirectional Remote Control
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
let controlChannel = null;
let ws = null;
let localStream = null;
let currentFacingMode = 'environment';
let isStreaming = false;
let wakeLock = null;
let torchOn = false;

const RESOLUTIONS = {
  '720': { width: 1280, height: 720 },
  '1080': { width: 1920, height: 1080 },
  '4k': { width: 3840, height: 2160 }
};

function handleRemoteCommand(cmd) {
  console.log("Remote command received from PC:", cmd);
  if (!cmd || !cmd.action) return;

  if (cmd.action === "set_res") {
    resSelect.value = String(cmd.value);
    initCamera().then(() => {
      if (isStreaming) {
        stopStream();
        startStream();
      }
    });
  } else if (cmd.action === "set_fps") {
    fpsSelect.value = String(cmd.value);
    initCamera().then(() => {
      if (isStreaming) {
        stopStream();
        startStream();
      }
    });
  } else if (cmd.action === "flip") {
    currentFacingMode = currentFacingMode === 'environment' ? 'user' : 'environment';
    initCamera().then(() => {
      if (isStreaming) {
        stopStream();
        startStream();
      }
    });
  } else if (cmd.action === "torch") {
    toggleTorch();
  }
}

function initWebSocketControl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  try {
    ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const cmd = JSON.parse(event.data);
        handleRemoteCommand(cmd);
      } catch (e) {}
    };
    ws.onclose = () => {
      setTimeout(initWebSocketControl, 2000);
    };
  } catch (e) {}
}

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
    audio: false,
    video: {
      facingMode: currentFacingMode,
      width: { ideal: target.width },
      height: { ideal: target.height },
      frameRate: { ideal: fpsChoice, min: 20, max: fpsChoice }
    }
  };

  try {
    localStream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = localStream;
    checkTorchSupport();
  } catch (err) {
    console.error("Camera Access Error:", err);
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
  } catch (err) {}
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
  pc = new RTCPeerConnection({ iceServers: [] });

  pc.ondatachannel = (event) => {
    controlChannel = event.channel;
    controlChannel.onmessage = (e) => {
      try {
        const cmd = JSON.parse(e.data);
        handleRemoteCommand(cmd);
      } catch (err) {}
    };
  };

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

  try {
    const params = sender.getParameters();
    if (!params.encodings || params.encodings.length === 0) {
      params.encodings = [{}];
    }
    params.degradationPreference = 'maintain-framerate';
    const fpsChoice = parseInt(fpsSelect.value, 10);
    const resChoice = resSelect.value;
    const targetBitrate = resChoice === '4k' ? 8000000 : (resChoice === '1080' ? 4500000 : 2500000);

    params.encodings[0].maxFramerate = fpsChoice;
    params.encodings[0].maxBitrate = targetBitrate;
    await sender.setParameters(params);
  } catch (e) {}

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
  initWebSocketControl();
});
