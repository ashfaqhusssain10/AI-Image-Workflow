const state = {
 currentPhase: 0,
 pollingInterval: null
};

// Polling for status updates
function startPolling() {
 if (state.pollingInterval) clearInterval(state.pollingInterval);
 state.pollingInterval = setInterval(async () => {
  try {
   const res = await fetch('/api/status');
   const data = await res.json();
   updateUI(data);
  } catch (e) {
   console.error("Polling error", e);
  }
 }, 1000);
}

function updateUI(data) {
 if (data.phase === state.currentPhase) return;
 state.currentPhase = data.phase;

 // Hide all views
 document.querySelectorAll('[id^=view-phase-]').forEach(el => el.classList.add('hidden'));

 // Update Progress Steps
 for (let i = 1; i <= 4; i++) {
  const step = document.getElementById(`step-${i}`);
  step.classList.remove('step-active', 'step-completed', 'text-white');
  if (i < data.phase) step.classList.add('step-completed');
  if (i === data.phase) step.classList.add('step-active');
 }

 // Show S3 Ref if available
 if (data.ref_image) {
  const refImg = document.getElementById('s3-ref-img');
  const refSidebar = document.getElementById('ref-sidebar');
  refImg.src = data.ref_image;
  refSidebar.classList.remove('hidden');
  setTimeout(() => refSidebar.classList.remove('opacity-0'), 100);
 }

 // Logic per Phase
 if (data.phase === 1) {
  // Just briefly show this, usually backend auto-skips to 2 once Ref is fetched
  document.getElementById('view-phase-1').classList.remove('hidden');
 }
 else if (data.phase === 2) {
  document.getElementById('view-phase-2').classList.remove('hidden');
 }
 else if (data.phase === 3) {
  document.getElementById('view-phase-3').classList.remove('hidden');
  // Check if generation finished
  fetch('/api/generate', { method: 'POST' });
  // Note: In real app, we shouldn't spam POST, but here the backend check handles idempotency safely enough
 }
 else if (data.phase === 4) {
  document.getElementById('view-phase-4').classList.remove('hidden');
  document.getElementById('generated-result').src = data.gen_image;
  // Pre-fill feedback if history
  if (data.prompt) document.getElementById('feedback-text').value = data.prompt;
 }
 else if (data.phase === 6) {
  document.getElementById('view-phase-6').classList.remove('hidden');
 }
}

// Upload Handling
function handleFileSelect(input, previewId) {
 const file = input.files[0];
 if (file) {
  const reader = new FileReader();
  reader.onload = (e) => {
   const preview = document.getElementById(previewId);
   preview.innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover rounded">`;
   preview.classList.add('border-blue-500');
  };
  reader.readAsDataURL(file);
 }
}

async function submitUploads() {
 const bgInput = document.getElementById('bg-input').files[0];
 const angleInput = document.getElementById('angle-input').files[0];

 if (!bgInput || !angleInput) {
  document.getElementById('upload-status').innerText = "Please upload both files.";
  return;
 }

 document.getElementById('upload-status').innerText = "Uploading...";

 const formData = new FormData();
 formData.append('background', bgInput);
 formData.append('angle', angleInput);

 await fetch('/api/upload', {
  method: 'POST',
  body: formData
 });
 // State polling will pick up the phase change
}

async function sendFeedback(action) {
 const prompt = document.getElementById('feedback-text').value;

 await fetch('/api/feedback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ action, prompt })
 });
}

async function resetWorkflow() {
 await fetch('/api/reset', { method: 'POST' });
 location.reload();
}

// Init
startPolling();
