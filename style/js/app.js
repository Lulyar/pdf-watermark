(function () {
  const form = document.getElementById("watermark-form");
  const pdfInput = document.getElementById("pdf");
  const pdfsInput = document.getElementById("pdfs");
  const opacitySlider = document.getElementById("opacity");
  const opacityValue = document.getElementById("opacity-value");
  const sizeSlider = document.getElementById("size_percent");
  const sizeValue = document.getElementById("size-value");
  const previewBtn = document.getElementById("preview-btn");
  const previewArea = document.getElementById("preview-area");
  const previewFrame = document.getElementById("preview-frame");
  const previewLoading = document.getElementById("preview-loading");
  const operationModeInput = document.getElementById("operation-mode");
  const watermarkSettings = document.getElementById("watermark-settings");
  const lockSettings = document.getElementById("lock-settings");
  const submitBtn = document.getElementById("submit-btn");
  const originalPassword = document.getElementById("original_password");
  const settingsPanel = document.getElementById("settings-panel");
  const uploadZone = document.getElementById("upload-zone");
  const uploadBtn = document.getElementById("upload-btn");
  const fileSelected = document.getElementById("file-selected");
  const fileSelectedName = document.getElementById("file-selected-name");
  const btnRemoveFile = document.getElementById("btn-remove-file");
  const heroTitle = document.getElementById("hero-title");
  const heroSubtitle = document.getElementById("hero-subtitle");

  // Mode configurations
  const modeConfig = {
    watermark: {
      title: "Tambah Watermark PDF",
      subtitle: "Tambahkan watermark ke file PDF kamu dengan mudah.",
      submitText: "Terapkan Watermark & Download",
      showWatermarkSettings: true,
      showLockSettings: false,
      showOriginalPassword: false,
      showPreview: true
    },
    compress: {
      title: "Kompres PDF",
      subtitle: "Kurangi ukuran file PDF tanpa mengorbankan kualitas.",
      submitText: "Compress & Download",
      showWatermarkSettings: false,
      showLockSettings: false,
      showOriginalPassword: false,
      showPreview: false
    },
    lock: {
      title: "Kunci PDF",
      subtitle: "Lindungi file PDF kamu dengan password enkripsi AES-256.",
      submitText: "Kunci & Download",
      showWatermarkSettings: false,
      showLockSettings: true,
      showOriginalPassword: true,
      showPreview: false
    },
    remove_password: {
      title: "Buka Kunci PDF",
      subtitle: "Hapus password dari file PDF yang terkunci.",
      submitText: "Hapus Password & Download",
      showWatermarkSettings: false,
      showLockSettings: false,
      showOriginalPassword: true,
      showPreview: false
    }
  };

  let currentMode = "watermark";

  // ===== Hamburger Menu =====
  var hamburgerBtn = document.getElementById("hamburger-btn");
  var navbarLinks = document.getElementById("navbar-links");
  if (hamburgerBtn && navbarLinks) {
    hamburgerBtn.addEventListener("click", function () {
      navbarLinks.classList.toggle("open");
    });
  }

  // ===== Navbar Navigation =====
  const navLinks = document.querySelectorAll(".nav-link[data-mode]");
  navLinks.forEach(function (link) {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const mode = this.dataset.mode;
      switchMode(mode);

      // Update active nav link
      navLinks.forEach(function (l) { l.classList.remove("active"); });
      link.classList.add("active");

      // Close mobile menu
      if (navbarLinks) navbarLinks.classList.remove("open");
    });
  });

  function switchMode(mode) {
    currentMode = mode;
    const config = modeConfig[mode];
    if (!config) return;

    // Update hidden input
    if (operationModeInput) operationModeInput.value = mode;

    // Update hero
    if (heroTitle) heroTitle.textContent = config.title;
    if (heroSubtitle) heroSubtitle.textContent = config.subtitle;

    // Update submit button
    if (submitBtn) submitBtn.textContent = config.submitText;

    // Show/hide watermark settings
    if (watermarkSettings) {
      watermarkSettings.style.display = config.showWatermarkSettings ? "block" : "none";
    }

    // Show/hide original password field
    var originalPasswordContainer = document.getElementById("original-password-container");
    if (originalPasswordContainer) {
      originalPasswordContainer.style.display = config.showOriginalPassword ? "block" : "none";
    }

    // Show/hide lock settings
    if (lockSettings) {
      lockSettings.style.display = config.showLockSettings ? "block" : "none";
    }

    // Show/hide preview button
    if (previewBtn) {
      previewBtn.style.display = config.showPreview ? "inline-block" : "none";
    }
    if (previewArea) previewArea.style.display = "none";

    // Reset file selection saat ganti mode — user wajib upload ulang
    resetFileSelection();
  }

  // ===== Upload Mode (Single / Batch) =====
  const uploadModeRadios = document.querySelectorAll('input[name="upload_mode"]');
  uploadModeRadios.forEach(function (radio) {
    radio.addEventListener("change", function () {
      resetFileSelection();
    });
  });

  function getUploadMode() {
    const checked = document.querySelector('input[name="upload_mode"]:checked');
    return checked ? checked.value : "single";
  }

  function getActiveInput() {
    return getUploadMode() === "batch" ? pdfsInput : pdfInput;
  }

  // ===== Upload Button =====
  if (uploadBtn) {
    uploadBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      getActiveInput().click();
    });
  }

  // Click on upload zone also triggers file select
  if (uploadZone) {
    uploadZone.addEventListener("click", function (e) {
      if (e.target === uploadBtn || e.target === btnRemoveFile || e.target.closest('.file-selected')) return;
      getActiveInput().click();
    });
  }

  // ===== File Selection =====
  function handleFileChange(input) {
    if (!input.files || input.files.length === 0) {
      resetFileSelection();
      return;
    }

    const isBatch = getUploadMode() === "batch";
    const count = input.files.length;

    if (isBatch && count > 1) {
      fileSelectedName.textContent = count + " file dipilih";
    } else {
      fileSelectedName.textContent = input.files[0].name;
    }

    // Show file indicator, hide upload content
    uploadZone.querySelector(".upload-zone-content").style.display = "none";
    fileSelected.style.display = "flex";
    uploadZone.classList.add("has-file");

    // Show settings panel
    if (settingsPanel) settingsPanel.style.display = "block";
  }

  if (pdfInput) {
    pdfInput.addEventListener("change", function () { handleFileChange(this); });
  }
  if (pdfsInput) {
    pdfsInput.addEventListener("change", function () { handleFileChange(this); });
  }

  // Remove file
  if (btnRemoveFile) {
    btnRemoveFile.addEventListener("click", function (e) {
      e.stopPropagation();
      resetFileSelection();
    });
  }

  function resetFileSelection() {
    if (pdfInput) pdfInput.value = "";
    if (pdfsInput) pdfsInput.value = "";

    uploadZone.querySelector(".upload-zone-content").style.display = "block";
    fileSelected.style.display = "none";
    uploadZone.classList.remove("has-file");

    if (settingsPanel) settingsPanel.style.display = "none";
    if (previewArea) previewArea.style.display = "none";
  }

  // ===== Drag & Drop =====
  if (uploadZone) {
    ["dragenter", "dragover"].forEach(function (evt) {
      uploadZone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach(function (evt) {
      uploadZone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.remove("drag-over");
      });
    });

    uploadZone.addEventListener("drop", function (e) {
      var files = e.dataTransfer.files;
      if (!files || files.length === 0) return;

      // Filter only PDF files
      var pdfFiles = [];
      for (var i = 0; i < files.length; i++) {
        if (files[i].name.toLowerCase().endsWith(".pdf")) {
          pdfFiles.push(files[i]);
        }
      }

      if (pdfFiles.length === 0) {
        alert("Hanya file PDF yang diperbolehkan.");
        return;
      }

      var input = getActiveInput();
      var dt = new DataTransfer();
      for (var j = 0; j < pdfFiles.length; j++) {
        dt.items.add(pdfFiles[j]);
      }
      input.files = dt.files;
      handleFileChange(input);
    });
  }

  // ===== Slider Updates =====
  if (opacitySlider && opacityValue) {
    opacitySlider.addEventListener("input", function () {
      opacityValue.textContent = this.value;
    });
  }

  if (sizeSlider && sizeValue) {
    sizeSlider.addEventListener("input", function () {
      sizeValue.textContent = this.value;
    });
  }

  // ===== Preview =====
  if (previewBtn) {
    previewBtn.addEventListener("click", async function () {
      var input = getActiveInput();
      if (!input.files || input.files.length === 0) {
        alert("Silakan pilih file PDF terlebih dahulu.");
        return;
      }

      var pdfFile = input.files[0];
      if (!pdfFile.name.toLowerCase().endsWith(".pdf")) {
        alert("Hanya file PDF yang diperbolehkan.");
        return;
      }

      previewArea.style.display = "block";
      previewLoading.style.display = "block";
      previewFrame.style.display = "none";

      try {
        var formData = new FormData();
        formData.append("pdf", pdfFile);

        var watermarkInput = document.getElementById("watermark");
        if (watermarkInput && watermarkInput.files && watermarkInput.files.length > 0) {
          formData.append("watermark", watermarkInput.files[0]);
        }

        formData.append("opacity", opacitySlider ? opacitySlider.value : "60");
        var posH = document.getElementById("position_h");
        var posV = document.getElementById("position_v");
        if (posH) formData.append("position_h", posH.value);
        if (posV) formData.append("position_v", posV.value);
        formData.append("size_percent", sizeSlider ? sizeSlider.value : "100");
        formData.append("operation_mode", currentMode);
        if (originalPassword) formData.append("original_password", originalPassword.value);

        var response = await fetch("/preview", {
          method: "POST",
          body: formData
        });

        if (!response.ok) throw new Error("Gagal membuat preview");

        var blob = await response.blob();
        var url = URL.createObjectURL(blob);
        previewFrame.src = url;
        previewFrame.style.display = "block";
        previewLoading.style.display = "none";
      } catch (error) {
        console.error("Preview error:", error);
        previewLoading.textContent = "Error: " + error.message;
        previewLoading.style.display = "block";
      }
    });
  }

  // ===== Form Submit =====
  if (form) {
    form.addEventListener("submit", function (e) {
      var isBatch = getUploadMode() === "batch";
      var input = getActiveInput();

      if (!input.files || input.files.length === 0) {
        e.preventDefault();
        alert("Silakan pilih file PDF terlebih dahulu.");
        return;
      }

      form.action = isBatch ? "/batch" : "/upload";
    });
  }
})();
