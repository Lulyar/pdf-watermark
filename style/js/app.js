(function () {
  const form = document.getElementById("watermark-form");
  const uploadMode = document.getElementById("upload-mode");
  const pdfInput = document.getElementById("pdf");
  const pdfsInput = document.getElementById("pdfs");
  const fileCountSpan = document.getElementById("file-count");
  const opacitySlider = document.getElementById("opacity");
  const opacityValue = document.getElementById("opacity-value");
  const sizeSlider = document.getElementById("size_percent");
  const sizeValue = document.getElementById("size-value");
  const previewBtn = document.getElementById("preview-btn");
  const previewArea = document.getElementById("preview-area");
  const previewFrame = document.getElementById("preview-frame");
  const previewLoading = document.getElementById("preview-loading");

  // Update opacity value display
  if (opacitySlider && opacityValue) {
    opacitySlider.addEventListener("input", function () {
      opacityValue.textContent = this.value;
    });
  }

  // Update size value display
  if (sizeSlider && sizeValue) {
    sizeSlider.addEventListener("input", function () {
      sizeValue.textContent = this.value;
    });
  }

  // Switch between single and batch upload
  if (uploadMode) {
    uploadMode.addEventListener("change", function () {
      const isBatch = this.value === "batch";
      pdfInput.style.display = isBatch ? "none" : "block";
      pdfsInput.style.display = isBatch ? "block" : "none";
      
      if (isBatch) {
        pdfsInput.setAttribute("required", "required");
        pdfInput.removeAttribute("required");
      } else {
        pdfInput.setAttribute("required", "required");
        pdfsInput.removeAttribute("required");
      }
      
      updateFileCount();
    });
  }

  // Update file count display
  function updateFileCount() {
    if (!fileCountSpan) return;
    const isBatch = uploadMode && uploadMode.value === "batch";
    const input = isBatch ? pdfsInput : pdfInput;
    
    if (isBatch && input.files.length > 0) {
      fileCountSpan.textContent = `(${input.files.length} file)`;
    } else {
      fileCountSpan.textContent = "";
    }
  }

  if (pdfInput) {
    pdfInput.addEventListener("change", updateFileCount);
  }
  if (pdfsInput) {
    pdfsInput.addEventListener("change", updateFileCount);
  }

  // Preview functionality
  if (previewBtn) {
    previewBtn.addEventListener("click", async function () {
      const isBatch = uploadMode && uploadMode.value === "batch";
      const pdfInputToUse = isBatch ? pdfsInput : pdfInput;
      
      if (!pdfInputToUse.files || pdfInputToUse.files.length === 0) {
        alert("Silakan pilih file PDF terlebih dahulu.");
        return;
      }

      // Untuk batch, ambil file pertama saja untuk preview
      const pdfFile = isBatch ? pdfInputToUse.files[0] : pdfInputToUse.files[0];
      
      if (!pdfFile.name.toLowerCase().endsWith(".pdf")) {
        alert("Hanya file PDF yang diperbolehkan.");
        return;
      }

      previewArea.style.display = "block";
      previewLoading.style.display = "block";
      previewFrame.style.display = "none";

      try {
        const formData = new FormData();
        formData.append("pdf", pdfFile);
        
        const watermarkInput = document.getElementById("watermark");
        if (watermarkInput.files && watermarkInput.files.length > 0) {
          formData.append("watermark", watermarkInput.files[0]);
        }
        
        formData.append("opacity", opacitySlider.value);
        formData.append("position_h", document.getElementById("position_h").value);
        formData.append("position_v", document.getElementById("position_v").value);
        formData.append("size_percent", sizeSlider.value);

        const response = await fetch("/preview", {
          method: "POST",
          body: formData
        });

        if (!response.ok) {
          throw new Error("Gagal membuat preview");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
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

  // Handle form submission - switch action based on mode
  if (form && uploadMode) {
    form.addEventListener("submit", function (e) {
      const isBatch = uploadMode.value === "batch";
      
      if (isBatch) {
        // Change form action to batch endpoint
        form.action = "/batch";
        
        // Rename input untuk batch
        if (pdfsInput.files.length === 0) {
          e.preventDefault();
          alert("Silakan pilih minimal satu file PDF untuk batch upload.");
          return;
        }
      } else {
        // Single file mode
        form.action = "/upload";
        
        if (!pdfInput.files || pdfInput.files.length === 0) {
          e.preventDefault();
          alert("Silakan pilih file PDF terlebih dahulu.");
          return;
        }
      }
    });
  }
})();

