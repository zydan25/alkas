(function () {
  const carousel = document.querySelector("[data-home-carousel]");
  if (!carousel) return;

  const slides = Array.from(carousel.querySelectorAll("[data-home-slide]"));
  const dots = Array.from(carousel.querySelectorAll("[data-home-dot]"));
  const prev = carousel.querySelector("[data-home-prev]");
  const next = carousel.querySelector("[data-home-next]");
  const pauseButton = carousel.querySelector("[data-home-pause]");
  const progress = carousel.querySelector("[data-home-progress]");
  const status = document.querySelector("[data-home-banner-status]");
  if (!slides.length) return;

  let index = 0;
  let timer = null;
  let paused = false;
  let hidden = document.hidden;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function durationFor(slide) {
    const value = Number(slide?.dataset.duration || 6);
    return Math.max(3, Math.min(60, Number.isFinite(value) ? value : 6));
  }

  function stopVideos() {
    slides.forEach((slide) => {
      slide.querySelectorAll("video").forEach((video) => {
        video.pause();
        try { video.currentTime = 0; } catch (_) {}
      });
    });
  }

  function resetProgress() {
    if (!progress) return;
    progress.style.transition = "none";
    progress.style.width = "0%";
    progress.offsetWidth;
  }

  function runProgress(duration) {
    if (!progress || paused || hidden || reducedMotion || slides.length < 2) return;
    progress.style.transition = `width ${duration}s linear`;
    requestAnimationFrame(() => {
      progress.style.width = "100%";
    });
  }

  function clearTimer() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function schedule() {
    clearTimer();
    resetProgress();

    if (paused || hidden || reducedMotion || slides.length < 2) return;

    const duration = durationFor(slides[index]);
    runProgress(duration);
    timer = setTimeout(() => goTo(index + 1), duration * 1000);
  }

  function playActiveVideo() {
    const video = slides[index]?.querySelector("video[data-home-video]");
    if (!video) return;

    video.muted = true;
    video.playsInline = true;
    const playPromise = video.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {
        if (status) status.textContent = "اضغط لتشغيل الفيديو";
      });
    }

    video.onended = () => {
      if (slides[index]?.contains(video)) goTo(index + 1);
    };
  }

  function updateUi() {
    slides.forEach((slide, slideIndex) => {
      const active = slideIndex === index;
      slide.classList.toggle("is-active", active);
      slide.setAttribute("aria-hidden", active ? "false" : "true");
    });

    dots.forEach((dot, dotIndex) => {
      const active = dotIndex === index;
      dot.classList.toggle("is-active", active);
      dot.setAttribute("aria-selected", active ? "true" : "false");
    });

    stopVideos();
    playActiveVideo();

    if (status) {
      status.textContent = paused ? "متوقف مؤقتًا" : `تشغيل تلقائي · ${durationFor(slides[index])} ث`;
    }
  }

  function goTo(target) {
    index = (target + slides.length) % slides.length;
    updateUi();
    schedule();
  }

  prev?.addEventListener("click", () => goTo(index - 1));
  next?.addEventListener("click", () => goTo(index + 1));

  dots.forEach((dot) => {
    dot.addEventListener("click", () => {
      const target = Number(dot.dataset.homeDot);
      if (Number.isInteger(target)) goTo(target);
    });
  });

  pauseButton?.addEventListener("click", () => {
    paused = !paused;
    pauseButton.textContent = paused ? "متابعة العرض" : "إيقاف مؤقت";
    pauseButton.setAttribute("aria-label", paused ? "متابعة العرض التلقائي" : "إيقاف العرض التلقائي");
    updateUi();
    schedule();
  });

  carousel.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") goTo(index - 1);
    if (event.key === "ArrowLeft") goTo(index + 1);
  });

  carousel.addEventListener("mouseenter", () => {
    if (reducedMotion) return;
    clearTimer();
    if (progress) {
      progress.style.transition = "none";
      progress.style.width = "0%";
    }
  });

  carousel.addEventListener("mouseleave", () => schedule());

  document.addEventListener("visibilitychange", () => {
    hidden = document.hidden;
    if (hidden) {
      clearTimer();
      slides[index]?.querySelectorAll("video").forEach((video) => video.pause());
    } else {
      playActiveVideo();
      schedule();
    }
  });

  updateUi();
  schedule();
})();
