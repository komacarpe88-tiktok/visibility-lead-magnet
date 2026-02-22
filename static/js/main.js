/* ============================================================
   LocalRankPro — Client-side JS
   ============================================================ */

// ── Landing Page: Loading overlay & form UX ──────────────────
(function () {
  const form    = document.getElementById('audit-form');
  const overlay = document.getElementById('loading-overlay');
  const btn     = document.getElementById('submit-btn');

  if (!form || !overlay) return;

  const steps = ['step-1', 'step-2', 'step-3', 'step-4'];
  let currentStep = 0;

  function advanceStep() {
    if (currentStep > 0) {
      const prev = document.getElementById(steps[currentStep - 1]);
      if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
    }
    if (currentStep < steps.length) {
      const cur = document.getElementById(steps[currentStep]);
      if (cur) cur.classList.add('active');
      currentStep++;
    }
  }

  form.addEventListener('submit', function (e) {
    // Basic client-side validation
    const required = form.querySelectorAll('[required]');
    let valid = true;
    required.forEach(function (field) {
      if (!field.value.trim()) {
        field.style.borderColor = '#E74C3C';
        field.addEventListener('input', function () {
          field.style.borderColor = '';
        }, { once: true });
        valid = false;
      }
    });

    if (!valid) {
      e.preventDefault();
      const firstInvalid = form.querySelector('[required]:not([value])');
      if (firstInvalid) firstInvalid.focus();
      return;
    }

    // Show loading overlay
    overlay.classList.remove('hidden');
    if (btn) { btn.disabled = true; btn.querySelector('.btn-text').textContent = 'Analyzing…'; }

    // Animate steps
    advanceStep(); // step 1 immediately
    setTimeout(advanceStep, 5000);   // step 2 at 5s
    setTimeout(advanceStep, 12000);  // step 3 at 12s
    setTimeout(advanceStep, 20000);  // step 4 at 20s
  });
})();


// ── Results Page: Gauge animation & score counter ────────────
(function () {
  if (typeof window.FINAL_SCORE === 'undefined') return;

  const finalScore = window.FINAL_SCORE;
  const gradeEl    = document.getElementById('gauge-grade');
  const scoreEl    = document.getElementById('gauge-score-display');
  const arc        = document.getElementById('gauge-arc');

  if (!arc || !scoreEl) return;

  // Arc parameters: the semi-circle path has total length ≈ 251.2 (π × r = π × 80)
  const ARC_LENGTH = 251.2;
  const gradeColors = {
    A: '#2ECC71',
    B: '#00B4D8',
    C: '#F39C12',
    D: '#FF7043',
    F: '#E74C3C',
  };

  // Set arc colour
  const grade = window.SCORE_GRADE || 'C';
  arc.style.stroke = gradeColors[grade] || '#1565C0';

  // Animate score counter 0 → finalScore
  let current = 0;
  const duration   = 1500; // ms
  const frameTime  = 16;
  const totalFrames = duration / frameTime;
  const increment  = finalScore / totalFrames;
  let frame = 0;

  const dashTarget = (finalScore / 100) * ARC_LENGTH;

  // Trigger arc animation on next frame (allows CSS transition to fire)
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      arc.style.strokeDasharray = dashTarget + ' ' + ARC_LENGTH;
    });
  });

  // Counter
  const timer = setInterval(function () {
    frame++;
    current = Math.min(Math.round(increment * frame), finalScore);
    if (scoreEl) scoreEl.textContent = current;
    if (frame >= totalFrames) {
      clearInterval(timer);
      if (scoreEl) scoreEl.textContent = finalScore;
    }
  }, frameTime);

  // Animate metric bar fills (start at 0, animate to their width)
  const bars = document.querySelectorAll('.metric-bar-fill');
  bars.forEach(function (bar) {
    const targetWidth = bar.style.width;
    bar.style.width = '0%';
    setTimeout(function () {
      bar.style.width = targetWidth;
    }, 300);
  });
})();
