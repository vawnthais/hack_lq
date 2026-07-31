document.addEventListener('DOMContentLoaded', () => {
    const webviewUrlInput = document.getElementById('webviewUrl');
    const picFileInput = document.getElementById('picFile');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const posterIdInput = document.getElementById('posterId');
    const encodeparamInput = document.getElementById('encodeparamInput');
    const posterForm = document.getElementById('posterForm');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = submitBtn.querySelector('.spinner');
    const btnText = submitBtn.querySelector('.btn-text');

    const parsedInfoBox = document.getElementById('parsedInfo');
    const infoPartition = document.getElementById('infoPartition');
    const infoRegion = document.getElementById('infoRegion');
    const infoToken = document.getElementById('infoToken');

    const previewImg = document.getElementById('previewImg');
    const imagePlaceholder = document.getElementById('imagePlaceholder');
    const previewNickname = document.getElementById('previewNickname');

    const responseBox = document.getElementById('responseBox');
    const responseTitle = document.getElementById('responseTitle');
    const responseText = document.getElementById('responseText');

    // Live URL Parser & Auto Fetch User Info from Garena
    webviewUrlInput.addEventListener('input', async () => {
        const urlStr = webviewUrlInput.value.trim();
        encodeparamInput.value = ''; // Auto clear encodeparam when URL changes!
        
        if (!urlStr) {
            parsedInfoBox.classList.add('hidden');
            return;
        }

        try {
            const urlObj = new URL(urlStr);
            const params = new URLSearchParams(urlObj.search);

            const partition = params.get('partition') || 'Chưa rõ';
            const region = params.get('aov_region') || 'Chưa rõ';
            const nickname = params.get('nickname');
            const token = params.get('itopencodeparam') || params.get('access_token');

            infoPartition.textContent = partition;
            infoRegion.textContent = region;
            infoToken.textContent = token ? 'Hợp lệ ✅' : 'Thiếu token ⚠️';

            if (nickname) {
                previewNickname.textContent = decodeURIComponent(nickname);
            }

            parsedInfoBox.classList.remove('hidden');

            // Gọi API getselfuserinfo lấy nickname chính xác từ game
            if (token) {
                try {
                    const infoRes = await fetch('/api/user-info', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ webview_url: urlStr })
                    });
                    const infoData = await infoRes.json();
                    if (infoData?.data?.nickName) {
                        previewNickname.textContent = infoData.data.nickName;
                    }
                    if (infoData?.data?.encryption) {
                        encodeparamInput.value = infoData.data.encryption;
                    }
                } catch (e) {
                    console.log("Could not auto-fetch user info", e);
                }
            }
        } catch (e) {
            parsedInfoBox.classList.add('hidden');
        }
    });

    // File Selection & Live Preview
    const fileUploadWrapper = document.querySelector('.file-upload-wrapper');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUploadWrapper.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadWrapper.addEventListener(eventName, () => {
            fileUploadWrapper.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileUploadWrapper.addEventListener(eventName, () => {
            fileUploadWrapper.classList.remove('dragover');
        }, false);
    });

    fileUploadWrapper.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            picFileInput.files = files; // Assign files to input
            
            // Trigger change event manually to update preview
            const event = new Event('change');
            picFileInput.dispatchEvent(event);
        }
    });

    function getCroppedBlob(file, targetRatio) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                let { width, height } = img;
                const imgRatio = width / height;

                let cropWidth = width;
                let cropHeight = height;
                let offsetX = 0;
                let offsetY = 0;

                if (imgRatio > targetRatio) {
                    cropWidth = height * targetRatio;
                    offsetX = (width - cropWidth) / 2;
                } else {
                    cropHeight = width / targetRatio;
                    offsetY = (height - cropHeight) / 2;
                }

                let finalWidth = 320;
                let finalHeight = 504;

                canvas.width = finalWidth;
                canvas.height = finalHeight;

                ctx.drawImage(
                    img,
                    offsetX, offsetY, cropWidth, cropHeight,
                    0, 0, finalWidth, finalHeight
                );

                const bypassAi = document.getElementById('bypassAiCheckbox');
                if (bypassAi && bypassAi.checked) {
                    const imageData = ctx.getImageData(0, 0, finalWidth, finalHeight);
                    const data = imageData.data;
                    for (let i = 0; i < data.length; i += 4) {
                        const noise = (Math.random() - 0.5) * 20; // Stronger noise
                        data[i] = Math.min(255, Math.max(0, data[i] + noise));
                        data[i+1] = Math.min(255, Math.max(0, data[i+1] + noise));
                        data[i+2] = Math.min(255, Math.max(0, data[i+2] + noise));
                        if (i % 8 === 0) data[i] = Math.max(0, data[i] - 5);
                        if (i % 12 === 0) data[i+2] = Math.min(255, data[i+2] + 5);
                    }
                    ctx.putImageData(imageData, 0, 0);

                    // Add a 3% opaque overlay of random tiny dots (salt and pepper)
                    ctx.fillStyle = "rgba(255, 255, 255, 0.03)";
                    for (let y = 0; y < finalHeight; y += 2) {
                        for (let x = 0; x < finalWidth; x += 2) {
                            if (Math.random() > 0.5) ctx.fillRect(x, y, 1, 1);
                        }
                    }

                    // Add dark scanlines to disrupt CNN max pooling
                    ctx.fillStyle = "rgba(0, 0, 0, 0.03)";
                    for (let y = 0; y < finalHeight; y += 4) {
                        ctx.fillRect(0, y, finalWidth, 1);
                    }
                    for (let x = 0; x < finalWidth; x += 4) {
                        ctx.fillRect(x, 0, 1, finalHeight);
                    }
                }
                
                canvas.toBlob((blob) => {
                    if (blob) resolve(blob);
                    else reject(new Error("Canvas to Blob failed"));
                }, 'image/png');
            };
            img.onerror = reject;
            img.src = URL.createObjectURL(file);
        });
    }

    let croppedFileBlob = null;

    picFileInput.addEventListener('change', async () => {
        const file = picFileInput.files[0];
        if (file) {
            fileNameDisplay.textContent = file.name;
            try {
                croppedFileBlob = await getCroppedBlob(file, 320 / 504);
                const previewUrl = URL.createObjectURL(croppedFileBlob);
                previewImg.src = previewUrl;
                previewImg.classList.remove('hidden');
                imagePlaceholder.classList.add('hidden');
            } catch (err) {
                console.error("Lỗi cắt ảnh:", err);
                // Fallback nếu cắt lỗi
                croppedFileBlob = file;
                previewImg.src = URL.createObjectURL(file);
                previewImg.classList.remove('hidden');
                imagePlaceholder.classList.add('hidden');
            }
        } else {
            croppedFileBlob = null;
            fileNameDisplay.textContent = 'Nhấn để chọn ảnh hoặc Kéo thả vào đây';
            previewImg.classList.add('hidden');
            imagePlaceholder.classList.remove('hidden');
        }
    });

    previewImg.addEventListener('error', () => {
        imagePlaceholder.textContent = 'Lỗi tải ảnh';
        imagePlaceholder.classList.remove('hidden');
        previewImg.classList.add('hidden');
    });

    const bypassAiCheckbox = document.getElementById('bypassAiCheckbox');
    if (bypassAiCheckbox) {
        bypassAiCheckbox.addEventListener('change', () => {
            if (picFileInput.files && picFileInput.files.length > 0) {
                picFileInput.dispatchEvent(new Event('change'));
            }
        });
    }

    // Form Submit
    posterForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const webviewUrl = webviewUrlInput.value.trim();
        const posterId = posterIdInput.value.trim() || '7562049';
        const encodeparam = encodeparamInput.value.trim();

        if (!webviewUrl || !croppedFileBlob) {
            alert('Vui lòng điền đầy đủ Link Webview và chọn một File Ảnh!');
            return;
        }

        // Show Spinner / Disable button
        submitBtn.disabled = true;
        btnText.textContent = 'ĐANG UPLOAD ẢNH...';
        spinner.classList.remove('hidden');
        responseBox.classList.add('hidden');

        try {
            // Gửi toàn bộ dữ liệu (file ảnh + url) về Backend của chúng ta
            const formData = new FormData();
            formData.append('file', croppedFileBlob, 'poster.png');
            formData.append('webview_url', webviewUrl);
            formData.append('poster_id', posterId);
            if (encodeparam) {
                formData.append('encodeparam', encodeparam);
            }

            btnText.textContent = 'ĐANG XỬ LÝ (TẢI ẢNH & ĐỔI POSTER)...';

            const res = await fetch('/api/change-poster', {
                method: 'POST',
                body: formData // Gửi dạng FormData thay vì JSON
            });

            const data = await res.json();

            responseBox.classList.remove('hidden', 'success', 'error');
            if (data.success) {
                responseBox.classList.add('success');
                responseTitle.textContent = '🎉 THÀNH CÔNG!';
            } else {
                responseBox.classList.add('error');
                responseTitle.textContent = '❌ THẤT BẠI';
            }

            responseText.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
            responseBox.classList.remove('hidden', 'success');
            responseBox.classList.add('error');
            responseTitle.textContent = '❌ LỖI HỆ THỐNG';
            responseText.textContent = err.message;
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '⚡ THAY ĐỔI ẢNH LOAD TRẬN';
            spinner.classList.add('hidden');
        }
    });
});
