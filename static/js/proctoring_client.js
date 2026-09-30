/**
 * PROJECT PANOPTICON - Real-Time AI Proctoring Client Engine
 */

let examStream = null;
let audioCtx = null;
let analyserNode = null;
let currentVolumeDb = 0;
let inferenceInterval = null;
let timerInterval = null;
let pendingBrowserEvent = null;
let pendingBrowserEventDetails = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initCameraAndAudio();
  initQuestionNavigation();
  initExamTimer();
  initBrowserSecurityListeners();
  initSubmitModal();
});

/* =========================================================================
   1. Camera & Audio Stream Initialization
   ========================================================================= */
async function initCameraAndAudio() {
  const video = document.getElementById('webcamVideo');

  try {
    examStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, frameRate: { ideal: 15 } },
      audio: true
    });

    if (video) {
      video.srcObject = examStream;
      video.play();
    }

    setupAudioAnalyser(examStream);
    console.log("[ProctoringClient] Webcam & microphone stream active.");
  } catch (err) {
    console.warn("[ProctoringClient] Physical webcam not accessible:", err);
    // Display server MJPEG feed fallback if physical webcam cannot be grabbed directly
    if (video) {
      video.style.display = 'none';
      const imgFallback = document.createElement('img');
      imgFallback.src = '/video_feed';
      imgFallback.alt = 'Server Proctoring Feed';
      video.parentNode.appendChild(imgFallback);
    }
  }

  // Launch AI inference loop at 1.5 FPS (every 650ms)
  inferenceInterval = setInterval(captureAndAnalyzeFrame, 650);
}

function setupAudioAnalyser(stream) {
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaStreamSource(stream);
    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 256;
    source.connect(analyserNode);

    const dataArray = new Uint8Array(analyserNode.frequencyBinCount);

    function computeVolume() {
      if (!analyserNode) return;
      analyserNode.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      let avg = sum / dataArray.length;
      // Map to approximate dB (0 to 100)
      currentVolumeDb = Math.min(100, Math.round((avg / 128) * 100));
      requestAnimationFrame(computeVolume);
    }
    computeVolume();
  } catch (e) {
    console.error("[ProctoringClient] Audio setup failed:", e);
  }
}

/* =========================================================================
   2. Frame Capture & AI Inference Loop
   ========================================================================= */
async function captureAndAnalyzeFrame() {
  const video = document.getElementById('webcamVideo');
  const attemptId = window.PANOPTICON_CONFIG.attemptId;

  let imageB64 = '';

  if (video && video.videoWidth > 0) {
    const canvas = document.createElement('canvas');
    canvas.width = 480;
    canvas.height = 360;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    imageB64 = canvas.toDataURL('image/jpeg', 0.65);
  } else {
    // If client camera is not accessible or hidden, send synthetic placeholder flag
    imageB64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';
  }

  const payload = {
    image: imageB64,
    attempt_id: attemptId,
    volume_db: currentVolumeDb,
    browser_event: pendingBrowserEvent,
    browser_event_details: pendingBrowserEventDetails
  };

  // Reset one-time browser event flag
  pendingBrowserEvent = null;
  pendingBrowserEventDetails = null;

  try {
    const res = await fetch('/api/proctoring/analyze_frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) return;

    const data = await res.json();
    updateProctoringHUD(data);

    if (data.warning) {
      triggerWarningNotification(data.warning);
    }
  } catch (err) {
    console.error("[ProctoringClient] Analysis request error:", err);
  }
}

/* =========================================================================
   3. Update HUD Display
   ========================================================================= */
function updateProctoringHUD(metrics) {
  // 1. Face Status
  const faceVal = document.getElementById('hudFace');
  if (faceVal) {
    if (metrics.face_count === 1) {
      faceVal.innerHTML = '<span style="color:var(--risk-normal)">1 Verified</span>';
    } else if (metrics.face_count === 0) {
      faceVal.innerHTML = '<span style="color:var(--risk-critical)">Missing</span>';
    } else {
      faceVal.innerHTML = `<span style="color:var(--risk-critical)">Multiple (${metrics.face_count})</span>`;
    }
  }

  // 2. Gaze Direction
  const gazeVal = document.getElementById('hudGaze');
  if (gazeVal) {
    gazeVal.innerText = metrics.gaze_direction || 'CENTER';
    gazeVal.style.color = metrics.is_looking_away ? 'var(--risk-warning)' : 'var(--text-main)';
  }

  // 3. Head Pose
  const headVal = document.getElementById('hudHead');
  if (headVal) {
    headVal.innerText = metrics.head_pose || 'FORWARD';
    headVal.style.color = (metrics.head_pose !== 'FORWARD') ? 'var(--risk-warning)' : 'var(--text-main)';
  }

  // 4. Mobile Phone
  const phoneVal = document.getElementById('hudPhone');
  if (phoneVal) {
    if (metrics.phone_detected) {
      phoneVal.innerHTML = `<span style="color:var(--risk-critical)">DETECTED (${Math.round(metrics.phone_confidence * 100)}%)</span>`;
    } else {
      phoneVal.innerHTML = '<span style="color:var(--text-dim)">Clear</span>';
    }
  }

  // 5. Audio Status
  const audioVal = document.getElementById('hudAudio');
  if (audioVal) {
    audioVal.innerText = metrics.audio_status || 'NORMAL';
    audioVal.style.color = (metrics.audio_status !== 'NORMAL') ? 'var(--risk-warning)' : 'var(--text-main)';
  }

  // 6. Risk Score & Status Badge
  const scoreVal = document.getElementById('hudRiskScore');
  const riskFill = document.getElementById('hudRiskFill');
  const statusBadge = document.getElementById('hudRiskStatus');

  if (scoreVal) {
    scoreVal.innerText = `${Math.round(metrics.current_risk)}%`;
  }

  if (riskFill) {
    riskFill.style.width = `${Math.min(100, metrics.current_risk)}%`;
  }

  if (statusBadge) {
    statusBadge.className = `status-pill status-${metrics.risk_status.toLowerCase()}`;
    statusBadge.innerHTML = `<span class="status-dot"></span> ${metrics.risk_status}`;
  }
}

/* =========================================================================
   4. Real-Time Warning Alert Banner
   ========================================================================= */
function triggerWarningNotification(warning) {
  const toast = document.getElementById('warningToast');
  const desc = document.getElementById('warningDesc');

  if (desc) desc.innerText = warning.description;
  if (toast) {
    toast.classList.add('show');
    playWarningBeep();

    setTimeout(() => {
      toast.classList.remove('show');
    }, 6000);
  }
}

function playWarningBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(600, ctx.currentTime);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  } catch (e) {}
}

/* =========================================================================
   5. Browser Security Events
   ========================================================================= */
function initBrowserSecurityListeners() {
  const attemptId = window.PANOPTICON_CONFIG.attemptId;

  // Visibility / Tab switch
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      reportSecurityEvent(attemptId, 'TAB_SWITCH', 'Candidate switched browser tab or minimized window.');
    }
  });

  // Window blur
  window.addEventListener('blur', () => {
    reportSecurityEvent(attemptId, 'WINDOW_BLUR', 'Candidate navigated outside browser window.');
  });

  // Fullscreen change
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) {
      reportSecurityEvent(attemptId, 'FULLSCREEN_EXIT', 'Candidate exited fullscreen mode.');
    }
  });

  // Clipboard protections
  document.addEventListener('copy', (e) => {
    reportSecurityEvent(attemptId, 'COPY_ACTION', 'Copy shortcut detected.');
  });

  document.addEventListener('paste', (e) => {
    reportSecurityEvent(attemptId, 'PASTE_ACTION', 'Paste shortcut detected.');
  });

  document.addEventListener('cut', (e) => {
    reportSecurityEvent(attemptId, 'CUT_ACTION', 'Cut shortcut detected.');
  });
}

async function reportSecurityEvent(attemptId, eventType, details) {
  pendingBrowserEvent = eventType;
  pendingBrowserEventDetails = details;

  try {
    const res = await fetch(`/api/exam/${attemptId}/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: eventType, details: details })
    });
    const data = await res.json();
    if (data.warning) {
      triggerWarningNotification(data.warning);
    }
  } catch (e) {
    console.error("[ProctoringClient] Failed to log security event:", e);
  }
}

/* =========================================================================
   6. Question Navigation & Instant Auto-Save
   ========================================================================= */
let currentQuestionIndex = 0;
const totalQuestions = window.PANOPTICON_CONFIG.totalQuestions;

function initQuestionNavigation() {
  showQuestion(0);

  // Next / Prev buttons
  const prevBtn = document.getElementById('prevQBtn');
  const nextBtn = document.getElementById('nextQBtn');

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentQuestionIndex > 0) {
        showQuestion(currentQuestionIndex - 1);
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentQuestionIndex < totalQuestions - 1) {
        showQuestion(currentQuestionIndex + 1);
      }
    });
  }

  // Palette buttons
  const paletteBtns = document.querySelectorAll('.palette-btn');
  paletteBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-index'));
      showQuestion(idx);
    });
  });

  // Option selection
  const optionItems = document.querySelectorAll('.option-item');
  optionItems.forEach(item => {
    item.addEventListener('click', () => {
      const qId = item.getAttribute('data-question-id');
      const opt = item.getAttribute('data-option');
      selectAndSaveAnswer(qId, opt, item);
    });
  });
}

function showQuestion(index) {
  currentQuestionIndex = index;
  const cards = document.querySelectorAll('.question-item-card');
  cards.forEach((card, i) => {
    card.style.display = (i === index) ? 'block' : 'none';
  });

  // Update button states
  const prevBtn = document.getElementById('prevQBtn');
  const nextBtn = document.getElementById('nextQBtn');
  if (prevBtn) prevBtn.disabled = (index === 0);
  if (nextBtn) nextBtn.disabled = (index === totalQuestions - 1);

  // Update palette highlight
  document.querySelectorAll('.palette-btn').forEach((btn, i) => {
    if (i === index) {
      btn.classList.add('current');
    } else {
      btn.classList.remove('current');
    }
  });
}

async function selectAndSaveAnswer(questionId, selectedOption, itemElement) {
  // Update visual selection in current question
  const parent = itemElement.closest('.options-list');
  parent.querySelectorAll('.option-item').forEach(el => el.classList.remove('selected'));
  itemElement.classList.add('selected');

  // Mark palette button as answered
  const paletteBtn = document.querySelector(`.palette-btn[data-question-id="${questionId}"]`);
  if (paletteBtn) paletteBtn.classList.add('answered');

  // Post answer to server
  const attemptId = window.PANOPTICON_CONFIG.attemptId;
  try {
    await fetch(`/api/exam/${attemptId}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: questionId, selected_option: selectedOption })
    });
  } catch (err) {
    console.error("[ProctoringClient] Failed to save answer:", err);
  }
}

/* =========================================================================
   7. Countdown Timer & Auto-Submit
   ========================================================================= */
function initExamTimer() {
  let secondsRemaining = window.PANOPTICON_CONFIG.remainingSeconds;
  const timerElement = document.getElementById('examCountdown');

  function updateTimer() {
    if (secondsRemaining <= 0) {
      clearInterval(timerInterval);
      timerElement.innerText = "00:00:00";
      autoSubmitExam();
      return;
    }

    secondsRemaining--;
    const h = Math.floor(secondsRemaining / 3600);
    const m = Math.floor((secondsRemaining % 3600) / 60);
    const s = secondsRemaining % 60;

    const formatted = [
      h > 0 ? String(h).padStart(2, '0') : null,
      String(m).padStart(2, '0'),
      String(s).padStart(2, '0')
    ].filter(Boolean).join(':');

    if (timerElement) {
      timerElement.innerText = formatted;
      if (secondsRemaining < 180) {
        timerElement.classList.add('urgent');
      }
    }
  }

  updateTimer();
  timerInterval = setInterval(updateTimer, 1000);
}

/* =========================================================================
   8. Submission Modal & Finalization
   ========================================================================= */
function initSubmitModal() {
  const openBtn = document.getElementById('openSubmitModalBtn');
  const modal = document.getElementById('submitModal');
  const cancelBtn = document.getElementById('cancelSubmitBtn');
  const confirmBtn = document.getElementById('confirmSubmitBtn');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      // Calculate answered count
      const answeredCount = document.querySelectorAll('.palette-btn.answered').length;
      document.getElementById('modalAnsweredCount').innerText = answeredCount;
      document.getElementById('modalRemainingCount').innerText = totalQuestions - answeredCount;
      modal.classList.add('open');
    });
  }

  if (cancelBtn && modal) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.remove('open');
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener('click', finalizeSubmission);
  }
}

async function autoSubmitExam() {
  alert("Time expired! Your exam will now be automatically submitted.");
  await finalizeSubmission();
}

async function finalizeSubmission() {
  clearInterval(inferenceInterval);
  clearInterval(timerInterval);

  if (examStream) {
    examStream.getTracks().forEach(track => track.stop());
  }

  const attemptId = window.PANOPTICON_CONFIG.attemptId;
  try {
    const res = await fetch(`/api/exam/${attemptId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
    } else {
      window.location.href = `/exam/${attemptId}/result`;
    }
  } catch (err) {
    console.error("[ProctoringClient] Submit error:", err);
    window.location.href = `/exam/${attemptId}/result`;
  }
}
