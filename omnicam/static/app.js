// OmniCam WebRTC Client - Bilingual EN (default) & RU
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
const langBtn = document.getElementById('lang-btn');

let pc = null;
let currentTrack = null;
let currentSender = null;
let controlChannel = null;
let currentFacingMode = 'environment';
let isStreaming = false;
let wakeLock = null;
let torchOn = false;

// i18n
let currentLang = localStorage.getItem('omnicam_lang') || 'en';

const UI_TEXT = {
  en: {
    ready: "READY",
    connecting: "CONNECTING...",
    live: "LIVE",
    startStream: "START STREAM",
    stopStream: "STOP STREAM",
    flip: "Flip Camera",
    torch: "Torch",
    badgeLang: "EN",
  },
  ru: {
    ready: "ГОТОВО",
    connecting: "ПОДКЛЮЧЕНИЕ...",
    live: "В ЭФИРЕ",
    startStream: "НАЧАТЬ СТРИМ",
    stopStream: "ОСТАНОВИТЬ СТРИМ",
    flip: "Сменить камеру",
    torch: "Фонарик",
    badgeLang: "RU",
  }
};

function applyLanguage(lang) {
  currentLang = lang === 'ru' ? 'ru' : 'en';
  localStorage.setItem('omnicam_lang', currentLang);
  const t = UI_TEXT[currentLang];

  langBtn.textContent = t.badgeLang;
  flipBtn.title = t.flip;
  torchBtn.title = t.torch;

  if (isStreaming) {
    statusText.textContent = t.live;
    btnLabel.textContent = t.stopStream;
  } else {
    statusText.textContent = t.ready;
    btnLabel.textContent = t.startStream;
  }
}

langBtn.addEventListener('click', () => {
  applyLanguage(currentLang === 'en' ? 'ru' : 'en');
});

// Standard 16:9 widescreen resolutions
const RESOLUTIONS = {
  '720': { width: 1280, height: 720 },
  '1080': { width: 1920, height: 1080 }
};

// --- Remote Commands Handler ---
async function handleRemoteCommand(cmd) {
  console.log("[Remote Command]", cmd);
  if (!cmd || !cmd.action) return;

  if (cmd.action === "set_res") {
    const val = String(cmd.value);
    if (val === "720" || val === "1080") {
      await changeResolution(val);
    }
  } else if (cmd.action === "set_fps") {
    await changeFps(parseInt(cmd.value, 10));
  } else if (cmd.action === "flip") {
    await flipCamera();
  } else if (cmd.action === "torch") {
    await toggleTorch();
  }
}

async function changeResolution(resChoice) {
  if (resChoice !== '720' && resChoice !== '1080') {
    resChoice = '1080';
  }
  resSelect.value = resChoice;
  statRes.textContent = `${resChoice}p`;
  const target = RESOLUTIONS[resChoice] || RESOLUTIONS['1080'];
  const fpsChoice = parseInt(fpsSelect.value, 10);

  if (currentTrack) {
    try {
      await currentTrack.applyConstraints({
        width: { ideal: target.width },
        height: { ideal: target.height },
        aspectRatio: { ideal: 1.7777777778 },
        frameRate: { ideal: fpsChoice, max: fpsChoice }
      });
      return;
    } catch (e) {
      console.warn("applyConstraints failed, falling back to replaceTrack:", e);
    }
  }
  await reinitCameraTrack();
}

async function changeFps(fpsChoice) {
  fpsSelect.value = String(fpsChoice);
  statFps.textContent = `${fpsChoice} FPS`;
  const resChoice = resSelect.value === '720' ? '720' : '1080';
  const target = RESOLUTIONS[resChoice];

  if (currentTrack) {
    try {
      await currentTrack.applyConstraints({
        width: { ideal: target.width },
        height: { ideal: target.height },
        aspectRatio: { ideal: 1.7777777778 },
        frameRate: { ideal: fpsChoice, max: fpsChoice }
      });
      return;
    } catch (e) {
      console.warn("applyConstraints failed, falling back to replaceTrack:", e);
    }
  }
  await reinitCameraTrack();
}

async function flipCamera() {
  currentFacingMode = currentFacingMode === 'environment' ? 'user' : 'environment';
  await reinitCameraTrack();
}

async function reinitCameraTrack() {
  const resChoice = resSelect.value === '720' ? '720' : '1080';
  const fpsChoice = parseInt(fpsSelect.value, 10) || 30;
  const target = RESOLUTIONS[resChoice];

  statRes.textContent = `${resChoice}p`;
  statFps.textContent = `${fpsChoice} FPS`;

  const constraints = {
    audio: false,
    video: {
      facingMode: currentFacingMode,
      width: { ideal: target.width },
      height: { ideal: target.height },
      aspectRatio: { ideal: 1.7777777778 },
      frameRate: { ideal: fpsChoice, max: fpsChoice }
    }
  };

  try {
    const newStream = await navigator.mediaDevices.getUserMedia(constraints);
    const newTrack = newStream.getVideoTracks()[0];

    if (currentTrack) {
      currentTrack.stop();
    }
    currentTrack = newTrack;
    video.srcObject = newStream;

    if (currentSender) {
      await currentSender.replaceTrack(newTrack);
    }
    checkTorchSupport();
  } catch (err) {
    console.error("Camera reinit error:", err);
  }
}

// --- Long-Polling for PC Remote Control ---
async function startCommandPolling() {
  while (true) {
    try {
      const res = await fetch('/poll-command', { cache: 'no-store' });
      if (res.ok) {
        const cmd = await res.json();
        if (cmd && cmd.action && cmd.action !== 'ping') {
          await handleRemoteCommand(cmd);
        }
      } else {
        await new Promise(r => setTimeout(r, 1000));
      }
    } catch (e) {
      await new Promise(r => setTimeout(r, 1000));
    }
  }
}

async function initCamera() {
  await reinitCameraTrack();
}

function checkTorchSupport() {
  if (!currentTrack) return;
  const capabilities = currentTrack.getCapabilities ? currentTrack.getCapabilities() : {};
  if (capabilities.torch) {
    torchBtn.style.display = 'flex';
  } else {
    torchBtn.style.display = 'none';
  }
}

async function toggleTorch() {
  if (!currentTrack) return;
  torchOn = !torchOn;
  try {
    await currentTrack.applyConstraints({
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
  if (!currentTrack) {
    await initCamera();
  }

  const t = UI_TEXT[currentLang];
  statusText.textContent = t.connecting;
  pc = new RTCPeerConnection({ iceServers: [] });

  pc.ondatachannel = (event) => {
    controlChannel = event.channel;
    controlChannel.onmessage = async (e) => {
      try {
        const cmd = JSON.parse(e.data);
        await handleRemoteCommand(cmd);
      } catch (err) {}
    };
  };

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'connected') {
      statusText.textContent = t.live;
      statusBadge.classList.add('streaming');
      streamBtn.classList.add('active');
      btnLabel.textContent = t.stopStream;
      isStreaming = true;
      requestWakeLock();
    } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
      stopStream();
    }
  };

  currentSender = pc.addTrack(currentTrack);

  try {
    const params = currentSender.getParameters();
    if (!params.encodings || params.encodings.length === 0) {
      params.encodings = [{}];
    }
    params.degradationPreference = 'maintain-framerate';
    const fpsChoice = parseInt(fpsSelect.value, 10) || 30;
    const resChoice = resSelect.value === '720' ? '720' : '1080';
    const targetBitrate = resChoice === '1080' ? 4500000 : 2500000;

    params.encodings[0].maxFramerate = fpsChoice;
    params.encodings[0].maxBitrate = targetBitrate;
    await currentSender.setParameters(params);
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
  currentSender = null;
  isStreaming = false;
  const t = UI_TEXT[currentLang];
  statusText.textContent = t.ready;
  statusBadge.classList.remove('streaming');
  streamBtn.classList.remove('active');
  btnLabel.textContent = t.startStream;
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

flipBtn.addEventListener('click', flipCamera);
torchBtn.addEventListener('click', toggleTorch);
resSelect.addEventListener('change', () => changeResolution(resSelect.value));
fpsSelect.addEventListener('change', () => changeFps(parseInt(fpsSelect.value, 10)));

window.addEventListener('DOMContentLoaded', () => {
  applyLanguage(currentLang);
  initCamera();
  startCommandPolling();
});
