<template>
  <section class="scanner">
    <h1 class="title">Scanner</h1>
    <p class="sub">Point the camera at the ticket QR code</p>

    <div class="preview-wrap">
      <video ref="videoEl" class="preview" playsinline muted autoplay></video>
      <canvas ref="canvasEl" class="hidden"></canvas>
      <div v-if="!cameraOn" class="camera-fallback">
        <p>{{ cameraMessage }}</p>
        <button class="btn" type="button" @click="startCamera">Enable Camera</button>
      </div>
    </div>

    <div class="actions">
      <button class="btn" type="button" :disabled="busy" @click="toggleCamera">
        {{ cameraOn ? "Stop Camera" : "Start Camera" }}
      </button>
      <router-link class="link" to="/scanner/manual">Manual search</router-link>
    </div>

    <details class="manual-token">
      <summary>Paste token manually</summary>
      <textarea v-model="token" rows="2" placeholder="v1....token..."></textarea>
      <button class="btn secondary" type="button" :disabled="busy || !token" @click="scanToken(token)">
        Check in
      </button>
    </details>

    <div v-if="result" class="result" :class="result.code">
      <strong>{{ result.code }}</strong>
      <p v-if="result.data?.attendee_name">{{ result.data.attendee_name }}</p>
      <p v-if="result.data?.ticket_type">{{ result.data.ticket_type }}</p>
      <p>{{ result.message }}</p>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue"
import { api } from "@/services/api"
import jsQR from "jsqr"

const videoEl = ref(null)
const canvasEl = ref(null)
const token = ref("")
const busy = ref(false)
const result = ref(null)
const cameraOn = ref(false)
const cameraMessage = ref("Camera permission needed for QR scanning.")
let stream = null
let rafId = null
let lastScanAt = 0

async function startCamera() {
  cameraMessage.value = "Requesting camera…"
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: { ideal: "environment" } },
    })
    videoEl.value.srcObject = stream
    await videoEl.value.play()
    cameraOn.value = true
    scanLoop()
  } catch (e) {
    cameraOn.value = false
    cameraMessage.value = "Camera blocked. Allow camera permission or use manual search."
  }
}

function stopCamera() {
  cameraOn.value = false
  if (rafId) cancelAnimationFrame(rafId)
  rafId = null
  if (stream) {
    stream.getTracks().forEach((t) => t.stop())
    stream = null
  }
}

function toggleCamera() {
  if (cameraOn.value) stopCamera()
  else startCamera()
}

function scanLoop() {
  if (!cameraOn.value || !videoEl.value || !canvasEl.value) return
  const video = videoEl.value
  const canvas = canvasEl.value
  const ctx = canvas.getContext("2d", { willReadFrequently: true })
  if (video.readyState === video.HAVE_ENOUGH_DATA) {
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const code = jsQR(image.data, image.width, image.height, { inversionAttempts: "dontInvert" })
    const now = Date.now()
    if (code?.data && now - lastScanAt > 2000 && !busy.value) {
      lastScanAt = now
      scanToken(code.data)
    }
  }
  rafId = requestAnimationFrame(scanLoop)
}

async function scanToken(raw) {
  const value = (raw || "").trim()
  if (!value) return
  busy.value = true
  result.value = { code: "VERIFYING", message: "Verifying…" }
  try {
    const res = await api("event_management.api.checkin.checkin_by_qr", { token: value })
    result.value = res
    if (navigator.vibrate) {
      navigator.vibrate(res.ok ? [40] : [30, 40, 30])
    }
    setTimeout(() => {
      if (result.value?.code !== "VERIFYING") result.value = null
    }, 2500)
  } catch (e) {
    result.value = { ok: false, code: "ERROR", message: e.message || "Check-in failed" }
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  if (navigator.mediaDevices?.getUserMedia) startCamera()
  else cameraMessage.value = "Camera API not available. Use manual search."
})

onBeforeUnmount(stopCamera)
</script>

<style scoped>
.scanner { max-width: 480px; margin: 0 auto; }
.title { font-family: var(--em-serif); font-size: 2rem; text-align: center; margin-bottom: .25rem; }
.sub { text-align: center; opacity: .7; margin-top: 0; }
.preview-wrap {
  position: relative; margin-top: 1rem; border-radius: 16px; overflow: hidden;
  background: #111; aspect-ratio: 3 / 4; max-height: 60vh;
}
.preview { width: 100%; height: 100%; object-fit: cover; display: block; }
.camera-fallback {
  position: absolute; inset: 0; display: grid; place-content: center; gap: .75rem;
  color: #fff; text-align: center; padding: 1rem; background: rgba(0,0,0,.55);
}
.hidden { display: none; }
.actions { display: flex; gap: .75rem; align-items: center; margin-top: .75rem; }
.btn {
  flex: 1; background: var(--em-accent); color: #fff; border: 0; border-radius: 10px;
  padding: .9rem 1rem; font-size: 1rem; font-weight: 700; cursor: pointer;
}
.btn.secondary { margin-top: .5rem; background: var(--em-ink); }
.link { opacity: .75; }
.manual-token { margin-top: 1rem; }
.manual-token textarea {
  width: 100%; margin-top: .5rem; padding: .75rem; border-radius: 10px;
  border: 1px solid var(--em-line); font-family: monospace;
}
.result {
  margin-top: 1rem; padding: 1rem; border-radius: 12px; text-align: center;
  animation: pop .25s ease;
}
.result.VALID { background: rgba(15,110,86,.15); }
.result.ALREADY_CHECKED_IN, .result.VERIFYING { background: rgba(196,92,38,.18); }
.result.INVALID_TOKEN, .result.CANCELLED, .result.UNPAID, .result.ERROR {
  background: rgba(155,28,28,.12);
}
@keyframes pop {
  from { transform: scale(.96); opacity: .4; }
  to { transform: scale(1); opacity: 1; }
}
</style>
