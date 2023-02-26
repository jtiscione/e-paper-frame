main = function(device) {
    console.log('device', device);

    let EPD_WIDTH = 128;
    let EPD_HEIGHT = 296;
    let AVAILABLE_COLORS = ['white', 'black'];

    if (device === 'EPD_2in13_B') {
        // 104x212 white/black/red
        // Two MONO_HLSB buffers (black first, red second)
        // buffer_black = bytearray(self.height * self.width // 8)
        // buffer_red = bytearray(self.height * self.width // 8)
        // imageblack = framebuf.FrameBuffer(self.buffer_black, self.width, self.height, framebuf.MONO_HLSB)
        // imagered = framebuf.FrameBuffer(self.buffer_red, self.width, self.height, framebuf.MONO_HLSB)
        EPD_WIDTH = 104
        EPD_HEIGHT = 212
        AVAILABLE_COLORS = ['white', 'black', 'red'];
    } else if (device === 'EPD_2in9_B') {
        // 128x296 white/black/red
        // Two MONO_HLSB buffers (black first, red second)
        // buffer_black = bytearray(self.height * self.width // 8)
        // buffer_red = bytearray(self.height * self.width // 8)
        // imageblack = framebuf.FrameBuffer(self.buffer_black, self.width, self.height, framebuf.MONO_HLSB)
        // imagered = framebuf.FrameBuffer(self.buffer_red, self.width, self.height, framebuf.MONO_HLSB)
        EPD_WIDTH = 128;
        EPD_HEIGHT = 296;
        AVAILABLE_COLORS = ['white', 'black', 'red'];
    } else if (device === 'EPD_3in7') {
        // One single GS2_HMSB buffer, 4 colors.
        // buffer_4Gray = bytearray(self.height * self.width // 4)
        // FrameBuffer(buffer_4Gray, self.width, self.height, framebuf.GS2_HMSB)
        EPD_WIDTH = 280;
        EPD_HEIGHT = 480;
        AVAILABLE_COLORS = ['white', 'lightgrey', 'darkgrey', 'black'];
    } else if (device === 'EPD_4in2') {
        // One single GS2_HMSB buffer, 4 colors.
        // buffer_4Gray = bytearray(self.height * self.width // 4)
        // FrameBuffer(self.buffer_4Gray, self.width, self.height, framebuf.GS2_HMSB)
        EPD_WIDTH = 400;
        EPD_HEIGHT = 300;
        AVAILABLE_COLORS = ['white', 'lightgrey', 'darkgrey', 'black']
    } else if (device === 'EPD_5in65') {
        // GS4_HMSB buffer, width * height // 2 bytes
        // buffer = bytearray(self.height * self.width // 2)
        // FrameBuffer(buffer, self.width, self.height, framebuf.GS4_HMSB)
        EPD_WIDTH = 600;
        EPD_HEIGHT = 448;
        AVAILABLE_COLORS = ['white', 'blank', 'black', 'red', 'orange', 'yellow', 'green', 'blue'];
    } else if (device === 'EPD_7in5_B') {
        // Two MONO HLSB buffers (black first, red second)
        EPD_WIDTH = 800
        EPD_HEIGHT = 480
        AVAILABLE_COLORS = ['white', 'black', 'red']
    }

   document.getElementById('caption').innerHTML = device;

    const PALETTE_COLORS = {
        white: [0xff, 0xff, 0xff],
        blank: [0xee, 0xee, 0xee],
        lightgrey: [0xd4, 0xd4, 0xd4],
        darkgrey: [0xaa, 0xaa, 0xaa],
        black: [0x00, 0x00, 0x00],
        red: [0xff, 0x00, 0x00],
        orange: [0xf1, 0x65, 0x29],
        yellow: [0xff, 0xff, 0x00],
        green: [0x00, 0xff, 0x00],
        blue: [0x00, 0x00, 0xff],
    };

    const PALETTE_WEIGHTS = {
        white: 1,
        blank: 1,
        lightgrey: 1,
        darkgrey: 1,
        black: 1,
        red: 1,
        orange: 0.5, // Not at an RGB cube vertex, not a neutral color; must be smaller target
        yellow: 1,
        green: 1,
        blue: 1,
    };

    const sidewaysCheckbox = document.getElementById('sideways-checkbox');
    const pane = document.getElementById('pane');
    let SIDEWAYS = (EPD_HEIGHT > EPD_WIDTH);
    if (SIDEWAYS) {
        pane.style.transform = 'rotate(-90deg)';
        sidewaysCheckbox.checked = true;
    }
    sidewaysCheckbox.addEventListener('change', (event) => {
        if (event.currentTarget.checked) {
            pane.style.transform = 'rotate(-90deg)';
            SIDEWAYS = true;
            if (EPD_WIDTH > EPD_HEIGHT) {
                // Wide canvas will cover controls if turned sideways
                pane.style.margin = `${(EPD_WIDTH - EPD_HEIGHT) / 2}px 0`;
            }
        } else {
            pane.style.transform = 'rotate(0)';
            SIDEWAYS = false;
            pane.style.margin = '0';
        }
    });

    const mainCanvas = document.getElementById('main-canvas');
    mainCanvas.width = EPD_WIDTH;
    mainCanvas.height = EPD_HEIGHT;
    const mainContext = mainCanvas.getContext('2d');
    mainContext.willReadFrequently = true;
    mainContext.fillStyle = AVAILABLE_COLORS.indexOf('blank') !== -1 ? '#eeeeee' : 'white';
    mainContext.fillRect(0, 0, mainCanvas.width, mainCanvas.height);

    const draggableCanvas = document.getElementById('draggable-canvas');
    const draggableContext = draggableCanvas.getContext('2d');
    draggableContext.willReadFrequently = true;

    const workCanvas = document.getElementById('work-canvas');
    workCanvas.style.display = 'block';
    workCanvas.width = EPD_WIDTH;
    workCanvas.height = EPD_HEIGHT;
    workCanvas.style.top = `${mainCanvas.offsetTop}px`;
    workCanvas.style.left = `${mainCanvas.offsetLeft}px`;
    const workContext = workCanvas.getContext('2d');

    const scaleSlider = document.getElementById('scale');
    const applyPasteButton = document.getElementById('apply-paste');
    const cancelPasteButton = document.getElementById('cancel-paste');

    const strokeWidthSlider = document.getElementById('stroke-width-slider');
    const strokeWidthValueIndicator = document.getElementById('stroke-width-value');
    strokeWidthValueIndicator.innerHTML = strokeWidthSlider.value;

    const paintButton = document.getElementById('paint-button');
    const drawBoxButton = document.getElementById('draw-box-button');
    const fillBoxButton = document.getElementById('fill-box-button');
    const textButton = document.getElementById('text-button');
    const clearButton = document.getElementById('clear-button');

    const fontNameSelect = document.getElementById('font-name-select');
    const fontSizeSelect = document.getElementById('font-size-select');

    const uploadButton = document.getElementById('upload-button');
    const printModal = document.getElementById('print-modal');
    const uploadStatus = document.getElementById('upload-status');
    const closeModalButton = document.getElementById('close-modal-button');

    const APP_MODES = {
        UNINITIALIZED: 'UNINITIALIZED',
        DEFAULT: 'DEFAULT',
        PASTE_OPERATION: 'PASTE_OPERATION',
        DRAWING: 'DRAWING',
        DRAW_BOX: 'DRAW_BOX',
        FILL_BOX: 'FILL_BOX',
        TEXT: 'TEXT',
        UPLOAD_OPERATION: 'UPLOAD_OPERATION',
    };

    let appMode = device ? APP_MODES.DEFAULT : APP_MODES.UNINITIALIZED;
    setAppMode(appMode);

    let pastedImage = undefined;
    let scalingFactor = 1.0;

    let selectedColor = 'black';

    const style = (color) => (color === 'blank' ? '#eeeeee' : color);

    let strokeWidth = parseInt(strokeWidthSlider.value);

    let fontName = 'Helvetica';
    let fontSize = '32pt';
    let text = '';

    // draggableCanvas is draggable if visible
    let dragging = false;
    let draggableMouseDownX = null;
    let draggableMouseDownY = null;

    draggableCanvas.addEventListener('mousedown', (e) => {
        dragging = true;
        let { x, y } = e;
        if (SIDEWAYS) {
            y = e.x;
            x = -e.y;
        }
        draggableMouseDownX = x;
        draggableMouseDownY = y;
        draggableCanvas.style.cursor = 'grabbing';
    });
    draggableCanvas.addEventListener('mousemove', (e) => {
        if (dragging) {
            let { x, y } = e;
            if (SIDEWAYS) {
                y = e.x;
                x = -e.y;
            }
            draggableCanvas.style.top = `${draggableCanvas.offsetTop + y - draggableMouseDownY}px`;
            draggableCanvas.style.left = `${draggableCanvas.offsetLeft + x - draggableMouseDownX}px`
            draggableMouseDownY = y;
            draggableMouseDownX = x;
        }
    });
    draggableCanvas.addEventListener('mouseup', (e) => {
        dragging = false;
        draggableMouseDownX = null;
        draggableMouseDownY = null;
        draggableCanvas.style.cursor = 'grab';
    });

    let mouseDownX = null;
    let mouseDownY = null;

    mainCanvas.addEventListener('mousedown', (e) => {
        if (appMode === APP_MODES.DEFAULT || appMode === APP_MODES.DRAWING || appMode === APP_MODES.DRAW_BOX || appMode === APP_MODES.FILL_BOX) {
            mouseDownX = e.offsetX;
            mouseDownY = e.offsetY;
            if (appMode === APP_MODES.DRAWING) {
                mainContext.fillStyle = style(selectedColor);
                mainContext.beginPath();
                mainContext.arc(mouseDownX, mouseDownY, strokeWidth / 2, 0, 2 * Math.PI);
                mainContext.closePath();
                mainContext.fill();
            }
        } else if (appMode === APP_MODES.TEXT) {
            draggableCanvas.style.top = `${mainCanvas.offsetTop + e.offsetY}px`;
            draggableCanvas.style.left = `${mainCanvas.offsetLeft + e.offsetX}px`;
            drawTextOnDraggableCanvas();
        }
    });

    mainCanvas.addEventListener('mousemove', (e) => {
        if (appMode === APP_MODES.DRAWING) {
            if (mouseDownX && mouseDownY) {
                mainContext.strokeStyle = style(selectedColor);
                mainContext.lineWidth = strokeWidth;
                mainContext.beginPath();
                mainContext.moveTo(mouseDownX, mouseDownY);
                mainContext.lineTo(e.offsetX, e.offsetY);
                mainContext.closePath();
                mainContext.stroke();
                mouseDownX = e.offsetX;
                mouseDownY = e.offsetY;
            }
        } else if (appMode === APP_MODES.DRAW_BOX || appMode === APP_MODES.FILL_BOX) {
            if (mouseDownX && mouseDownY) {
                workContext.clearRect(0, 0, workCanvas.width, workCanvas.height);
                if (appMode === APP_MODES.DRAW_BOX) {
                    workContext.strokeStyle = style(selectedColor);
                    workContext.lineWidth = strokeWidth;
                    workContext.strokeRect(mouseDownX, mouseDownY, e.offsetX - mouseDownX, e.offsetY - mouseDownY);
                } else {
                    workContext.fillStyle = style(selectedColor);
                    workContext.fillRect(mouseDownX, mouseDownY, e.offsetX - mouseDownX, e.offsetY - mouseDownY);
                }
            }
        }
    });

    const mouseUpListener = (e) => {
        mouseDownX = undefined;
        mouseDownY = undefined;
        mainContext.drawImage(workCanvas, 0, 0);
        workContext.clearRect(0, 0, workCanvas.width, workCanvas.height);
    }

    mainCanvas.addEventListener('mouseup', mouseUpListener);

    function setAppMode(mode) {
        // console.log(`changing setAppMode from ${appMode} to ${mode}`);
        const {
            UNINITIALIZED, DEFAULT, PASTE_OPERATION, DRAWING, DRAW_BOX, FILL_BOX, TEXT, UPLOAD_OPERATION
        } = APP_MODES;

        function anyOf(...modes) {
            return modes.indexOf(appMode) !== -1;
        }

        appMode = mode;
        scaleSlider.disabled = (appMode !== PASTE_OPERATION);
        applyPasteButton.disabled = (appMode !== PASTE_OPERATION);
        cancelPasteButton.disabled = (appMode !== PASTE_OPERATION);
        uploadButton.disabled = anyOf(PASTE_OPERATION, TEXT, UPLOAD_OPERATION, UNINITIALIZED);

        if (anyOf(DEFAULT, DRAW_BOX, FILL_BOX, DRAWING, UPLOAD_OPERATION, UNINITIALIZED)) {
            draggableCanvas.style.display = 'none';
        }

        sidewaysCheckbox.disabled = anyOf(TEXT, PASTE_OPERATION, UPLOAD_OPERATION, UNINITIALIZED);
        strokeWidthSlider.disabled = anyOf(DEFAULT, FILL_BOX, TEXT, PASTE_OPERATION, UPLOAD_OPERATION, UNINITIALIZED);
        if (appMode === TEXT) {
            text = '';
            draggableCanvas.style.top = `${mainCanvas.offsetTop}px`;
            draggableCanvas.style.left = `${mainCanvas.offsetLeft}px`;
            draggableCanvas.width = 0; // for now
            draggableCanvas.height = 0; // for now
            draggableCanvas.style.display = 'block';
        }
        mainCanvas.style.cursor = (appMode === TEXT ? 'text' : (appMode === UPLOAD_OPERATION ? 'wait' : 'crosshair'));

        const c_names = (mode) => (appMode === mode ? 'toolbar-button toolbar-button-selected' : 'toolbar-button');

        paintButton.className = c_names(DRAWING);
        drawBoxButton.className = c_names(DRAW_BOX);
        fillBoxButton.className = c_names(FILL_BOX);
        textButton.className = c_names(TEXT);

        paintButton.disabled = anyOf(UPLOAD_OPERATION, UNINITIALIZED);
        drawBoxButton.disabled = anyOf(UPLOAD_OPERATION, UNINITIALIZED);
        fillBoxButton.disabled = anyOf(UPLOAD_OPERATION, UNINITIALIZED);
        textButton.disabled = anyOf(UPLOAD_OPERATION, UNINITIALIZED);
        clearButton.disabled = anyOf(UPLOAD_OPERATION, UNINITIALIZED);

        fontNameSelect.disabled = (appMode !== TEXT);
        fontSizeSelect.disabled = (appMode !== TEXT);
    }

    /*
     * This is a function for performing the non-trivial task of identifying which color in the palette is closest match
     * for an arbitrary input color.
     */
    function findClosestPaletteColor(r, g, b) {
        // This is a really trivial implementation that can probably be improved
        let lowestColor = undefined;
        let lowestDistance = 1000;
        AVAILABLE_COLORS.forEach((color) => {
            const [paletteRed, paletteGreen, paletteBlue] = PALETTE_COLORS[color];
            const weight = PALETTE_WEIGHTS[color];
            const distance = Math.sqrt(
                (r - paletteRed) * (r - paletteRed)
                + (g - paletteGreen) * (g - paletteGreen)
                + (b - paletteBlue) * (b - paletteBlue)
            ) / weight;
            // faster: const distance = Math.abs(r - paletteRed) + Math.abs(g - paletteGreen) + Math.abs(b - paletteBlue);
            if (distance < lowestDistance) {
                lowestColor = color;
                lowestDistance = distance;
            }
        });
        return lowestColor;
    }

    function distributeErrorToNeighbors(imgData, width, index, error) {
        const len = imgData.length;
        let target_index = index + 4;
        if (target_index < len) {
            imgData[target_index] += (error * 7) >> 4;
        }
        target_index = index + 4 * (width - 1);
        if (target_index < len) {
            imgData[target_index] += (error * 3) >> 4;
        }
        target_index = index + 4 * width;
        if (target_index < len) {
            imgData[target_index] += (error * 5) >> 4;
        }
        target_index = index + 4 * (width + 1)
        if (target_index < len) {
            imgData[target_index] += error > 4;
        }
    }

    function performDither(canvas, context, distributeError = true) {
        // dithers the contents of the canvas; sets each pixel to one of AVAILABLE_COLORS
        const { width, height } = canvas;
        const imgData = context.getImageData(0,0, width, height);
        const data = imgData.data;
        // Apply Floyd-Steinberg dithering algorithm
        let index = 0
        for (let j = 0; j < height; j++) {
            for (let i = 0; i < width; i++) {
                const red = data[index];
                const green = data[index + 1];
                const blue = data[index + 2];
                const [ new_red, new_green, new_blue] = PALETTE_COLORS[findClosestPaletteColor(red, green, blue)];
                data[index] = new_red;
                data[index + 1] = new_green;
                data[index + 2] = new_blue;
                const error_red = red - new_red;
                const error_green = green - new_green;
                const error_blue = blue - new_blue;
                if (distributeError) {
                    distributeErrorToNeighbors(data, width, index, error_red);
                    distributeErrorToNeighbors(data, width,index + 1, error_green);
                    distributeErrorToNeighbors(data, width,index + 2, error_blue);
                }
                index += 4;
            }
        }
        context.putImageData(imgData, 0, 0);
    }

    // white / black / red
    function extractHLSBFromCanvasBlackRed(canvas, include_red=true) {
        const imageData = mainContext.getImageData(0, 0, canvas.width, canvas.height);
        const buffer = imageData.data.buffer;  // ArrayBuffer
        const byteBuffer = new Uint8ClampedArray(buffer);

        const black_MONO_HLSB = new Uint8Array((canvas.width >> 3) * canvas.height);
        const red_MONO_HLSB = include_red
            ? new Uint8Array((canvas.width >> 3) * canvas.height)
            : undefined;

        let buffer_index = 0;
        let hlsb_index = 0;
        let bitshift = 7;

        for (let y = 0; y < canvas.height; y++) {
            for (let x = 0; x < canvas.width; x++) {
                const red = byteBuffer[buffer_index++]
                const green = byteBuffer[buffer_index++]
                const blue = byteBuffer[buffer_index++];
                const alpha = byteBuffer[buffer_index++];
                const color = findClosestPaletteColor(red, green, blue, alpha);
                let hlsb = undefined;
                if (color === 'black') {
                    hlsb = black_MONO_HLSB
                }
                if (include_red && color === 'red') {
                    hlsb = red_MONO_HLSB;
                }
                if (hlsb) {
                    hlsb[hlsb_index] |= (1 << bitshift);
                }
                if (bitshift === 0) {
                    bitshift += 8;
                    hlsb_index++;
                }
                bitshift--;
            }
        }
        for (let index = 0; index < black_MONO_HLSB.length; index++) {
            black_MONO_HLSB[index] = ~black_MONO_HLSB[index];
            if (include_red) {
                red_MONO_HLSB[index] = ~red_MONO_HLSB[index];
            }
        }
        const b64_encoded_black = btoa(String.fromCharCode.apply(null, black_MONO_HLSB))
        if (!include_red) {
            return [ b64_encoded_black ];
        }
        const b64_encoded_red = btoa(String.fromCharCode.apply(null, red_MONO_HLSB))
        return [
            b64_encoded_black,
            b64_encoded_red,
        ];
    }

    // Grayscale 4 color
    function extractHLSBFromCanvasGray4(canvas, flipGreys=false) {
        const imageData = mainContext.getImageData(0, 0, canvas.width, canvas.height);
        const buffer = imageData.data.buffer;  // ArrayBuffer
        const byteBuffer = new Uint8ClampedArray(buffer);

        const first_HLSB = new Uint8Array((canvas.width >> 3) * canvas.height);
        const second_HLSB = new Uint8Array((canvas.width >> 3) * canvas.height);

        let buffer_index = 0;
        let hlsb_index = 0;
        let bitshift = 7;

        for (let y = 0; y < canvas.height; y++) {
            for (let x = 0; x < canvas.width; x++) {
                const red = byteBuffer[buffer_index++];
                const green = byteBuffer[buffer_index++];
                const blue = byteBuffer[buffer_index++];
                const alpha = byteBuffer[buffer_index++];
                const color = findClosestPaletteColor(red, green, blue, alpha);
                if (flipGreys) {
                    if (color === 'white' || color === 'lightgrey') {
                        first_HLSB[hlsb_index] |= (1 << bitshift);
                    }
                    if (color === 'white' || color === 'darkgrey') {
                        second_HLSB[hlsb_index] |= (1 << bitshift);
                    }
                } else {
                    if (color === 'white' || color === 'darkgrey') {
                        first_HLSB[hlsb_index] |= (1 << bitshift);
                    }
                    if (color === 'white' || color === 'lightgrey') {
                        second_HLSB[hlsb_index] |= (1 << bitshift);
                    }
                }
                if (bitshift === 0) {
                    bitshift += 8;
                    hlsb_index++;
                }
                bitshift--;
            }
        }
        return [
            btoa(String.fromCharCode.apply(null, first_HLSB)),
            btoa(String.fromCharCode.apply(null, second_HLSB)),
        ];
    }

    // 7 color
    function extractHMSBFromCanvas(canvas) {
        const imageData = mainContext.getImageData(0, 0, canvas.width, canvas.height);
        const buffer = imageData.data.buffer;  // ArrayBuffer
        const byteBuffer = new Uint8ClampedArray(buffer);

        const NUM_BLOCKS = 8;
        const bands = [];

        for (let i = 0; i < NUM_BLOCKS; i++) {
            bands.push(new Uint8Array(canvas.width * canvas.height / (2 * NUM_BLOCKS)));
        }

        const toColorCode = (color) => {
            if (color === 'black') {
                return 0x00;
            }
            if (color === 'white') {
                return 0x01;
            }
            if (color === 'green') {
                return 0x02;
            }
            if (color === 'blue') {
                return 0x03;
            }
            if (color === 'red') {
                return 0x04;
            }
            if (color === 'yellow') {
                return 0x05;
            }
            if (color === 'orange') {
                return 0x06;
            }
            return 0x07; // the blank or "clean" color
        }

        let buffer_index = 0;

        const band_height = (canvas.height / NUM_BLOCKS);
        for (let y = 0; y < canvas.height; y++) {
            const band_number = Math.floor(y / band_height);
            const band = bands[band_number];
            let band_index = (canvas.width / 2) * (y - (band_height * band_number));
            for (let x = 0; x < canvas.width; x += 2) {
                const red1 = byteBuffer[buffer_index++]
                const green1 = byteBuffer[buffer_index++]
                const blue1 = byteBuffer[buffer_index++];
                const alpha1 = byteBuffer[buffer_index++];
                const color1 = toColorCode(findClosestPaletteColor(red1, green1, blue1, alpha1));
                const red2 = byteBuffer[buffer_index++]
                const green2 = byteBuffer[buffer_index++]
                const blue2 = byteBuffer[buffer_index++];
                const alpha2 = byteBuffer[buffer_index++];
                const color2 = toColorCode(findClosestPaletteColor(red2, green2, blue2, alpha2));
                band[band_index++] = (color1 << 4) | color2;
            }
        }

        const b64_buffers = bands.map((band) => btoa(String.fromCharCode.apply(null, band)));
        // console.log(b64_buffers);
        return b64_buffers;
    }

    function updateUploadStatus(additionalLine) {
        uploadStatus.innerHTML += `<div>${additionalLine}</div>`;
    }

    async function sequentialPost(buffers) {
        let block = 0;
        let sequence_retries = 0; // max 3
        let block_retries = 0; // max 2
        while (appMode === APP_MODES.UPLOAD_OPERATION && block < buffers.length && sequence_retries < 3) {
            updateUploadStatus(`Uploading block ${block + 1} of ${buffers.length}${block_retries ? " (retry #"+block_retries+")" : ""}...`);
            const response = await fetch(`/block${block}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: buffers[block],
            });
            updateUploadStatus(`${response.status} ${response.statusText}`);
            console.log(`${response.status} ${response.statusText}`);
            if (response.status >= 200 && response.status < 300) {
                block_retries = 0;
                block++;
            } else if (response.status === 409) {
                updateUploadStatus(`Restarting sequence...`);
                block_retries = 0;
                sequence_retries++;
                block = 0;
            } else {
                block_retries += 1;
                if (block_retries > 2) {
                    block_retries = 0;
                    sequence_retries++;
                    block = 0;
                }
                await new Promise((resolve) => setTimeout(resolve,1000));
            }
        }
        if (block === buffers.length) {
            updateUploadStatus('SUCCESS.');
        } else if (appMode !== APP_MODES.UPLOAD_OPERATION) {
            updateUploadStatus("Canceled.");
        } else {
            updateUploadStatus("Upload failed.");
        }
        setAppMode(APP_MODES.DEFAULT);
    }

    closeModalButton.addEventListener('click', (e) => {
        if (appMode === APP_MODES.UPLOAD_OPERATION) {
            setAppMode(APP_MODES.DEFAULT);
        } else {
            printModal.style.display = 'none';
            uploadStatus.innerHTML = "";
        }
    });

    async function uploadCanvas() {
        setAppMode(APP_MODES.UPLOAD_OPERATION);
        printModal.style.display = 'block';
        if (device === 'EPD_2in13_B' || device === 'EPD_2in9_B') {
            const [black, red] = extractHLSBFromCanvasBlackRed(mainCanvas);
            sequentialPost([black, red]);
        } else if (device === 'EPD_3in7') {
            const b64_buffers = extractHLSBFromCanvasGray4(mainCanvas);
            sequentialPost(b64_buffers);
        } else if (device === 'EPD_4in2') {
            const b64_buffers = extractHLSBFromCanvasGray4(mainCanvas, true);
            sequentialPost(b64_buffers);
        } else if (device === 'EPD_5in65') {
            const b64_buffers = extractHMSBFromCanvas(mainCanvas);
            sequentialPost(b64_buffers);
        } else if (device === 'EPD_7in5_B') {
            const [black, red] = extractHLSBFromCanvasBlackRed(mainCanvas)
            // These are each 48000 bytes; split each into four chunks of 12000
            quarter = black.length / 4
            sequentialPost([
                black.subarray(0, quarter),
                black.subarray(quarter, 2 * quarter),
                black.subarray(2 * quarter, 3 * quarter),
                black.subarray(3 * quarter, 4 * quarter),
                red.subarray(0, quarter),
                red.subarray(quarter, 2 * quarter),
                red.subarray(2 * quarter, 3 * quarter),
                red.subarray(3 * quarter, 4 * quarter),
            ]);
        }
        closeModalButton.disabled = false;
    }

    //on paste INTO the canvas
    function paste_auto(e) {
        if (e.clipboardData) {
            let items = e.clipboardData.items;
            if (!items) {
                return;
            }
            //access data directly
            let is_image = false;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf("image") !== -1) {
                    //image
                    setAppMode(APP_MODES.PASTE_OPERATION);
                    let blob = items[i].getAsFile();
                    let URLObj = window.URL || window.webkitURL;
                    let source = URLObj.createObjectURL(blob);
                    paste_createImage(source);
                    is_image = true;
                }
            }
            if(is_image){
                e.preventDefault();
            }
        }
    }

    //draw externally pasted image to draggableCanvas
    function paste_createImage(source) {
        pastedImage = new Image();
        pastedImage.onload = function () {
            let pastedImageWidth = pastedImage.width;
            let pastedImageHeight = pastedImage.height;
            if (SIDEWAYS) {
                const swap = pastedImageHeight;
                pastedImageHeight = pastedImageWidth;
                pastedImageWidth = swap;
            }
            if (pastedImageWidth / pastedImageHeight > mainCanvas.width / mainCanvas.height) {
                scalingFactor = mainCanvas.width / pastedImageWidth;
                draggableCanvas.width = mainCanvas.width;
                draggableCanvas.height = pastedImageHeight * scalingFactor;
                draggableCanvas.style.left = "0px"; // `${canvas.offsetLeft}px`;
                draggableCanvas.style.top = "0px"; // `${canvas.offsetTop + (canvas.height - draggableCanvas.height) / 2}px`;
            } else {
                scalingFactor = mainCanvas.height / pastedImageHeight;
                draggableCanvas.height = mainCanvas.height;
                draggableCanvas.width = pastedImageWidth * scalingFactor;
                draggableCanvas.style.left = "0px"; // `${canvas.offsetLeft + (canvas.width - draggableCanvas.width) / 2}px`;
                draggableCanvas.style.top = "0px"; // `${canvas.offsetTop}px`;
            }
            scaleSlider.value = 100 * scalingFactor;
            if (SIDEWAYS) {
                draggableContext.save();
                draggableContext.translate(draggableCanvas.width / 2, draggableCanvas.height / 2);
                draggableContext.rotate(Math.PI / 2);
                draggableContext.drawImage(pastedImage, -draggableCanvas.height / 2, -draggableCanvas.width / 2, draggableCanvas.height, draggableCanvas.width);
                draggableContext.restore();
            } else {
                draggableContext.drawImage(pastedImage, 0, 0, draggableCanvas.width, draggableCanvas.height);
            }

            performDither(draggableCanvas, draggableContext);
            draggableCanvas.style.display = 'block';
        }
        pastedImage.src = source;
    }

    function adjustScalingFactor(s) {
        scalingFactor = s;
        if (SIDEWAYS) {
            draggableCanvas.width = pastedImage.height * scalingFactor;
            draggableCanvas.height = pastedImage.width * scalingFactor;
            draggableContext.save();
            draggableContext.translate(draggableCanvas.width / 2, draggableCanvas.height / 2);
            draggableContext.rotate(Math.PI / 2);
            draggableContext.drawImage(pastedImage, -draggableCanvas.height / 2, -draggableCanvas.width / 2, draggableCanvas.height, draggableCanvas.width);
            draggableContext.restore();
        } else {
            draggableCanvas.width = pastedImage.width * scalingFactor;
            draggableCanvas.height = pastedImage.height * scalingFactor;
            draggableContext.drawImage(pastedImage, 0, 0, draggableCanvas.width, draggableCanvas.height);
        }
        performDither(draggableCanvas, draggableContext);
    }

    document.addEventListener('paste', function (e) {
        paste_auto(e);
    }, false);

    scaleSlider.addEventListener('input', (e) => {
        if (appMode === APP_MODES.PASTE_OPERATION) {
            const scale = parseInt(e.target.value) / 100;
            adjustScalingFactor(scale);
        }
    });

    strokeWidthSlider.addEventListener('input', (e) => {
        strokeWidth = parseInt(e.target.value);
        strokeWidthValueIndicator.innerHTML = e.target.value;
    });

    const transferDraggableToMain = () => {
        if (appMode === APP_MODES.PASTE_OPERATION || appMode === APP_MODES.TEXT) {
            mainContext.drawImage(draggableCanvas, draggableCanvas.offsetLeft - mainCanvas.offsetLeft, draggableCanvas.offsetTop - mainCanvas.offsetTop);
            performDither(mainCanvas, mainContext, (appMode !== APP_MODES.TEXT));
            setAppMode(APP_MODES.DEFAULT);
        }
    }

    applyPasteButton.addEventListener('click', transferDraggableToMain);

    cancelPasteButton.addEventListener('click', (e) => {
        setAppMode(APP_MODES.DEFAULT);
    });

    Array.prototype.forEach.call(document.getElementsByClassName('palette-button'), function(button) {
        if (AVAILABLE_COLORS.indexOf(button.id) < 0) {
            button.style.display = 'none';
        } else {
            button.addEventListener('click', (e) => {
                document.getElementById(selectedColor).className="palette-button"; // removes palette-button-selected
                selectedColor = button.id;
                document.getElementById(selectedColor).className="palette-button palette-button-selected";
                if (appMode === APP_MODES.TEXT) {
                    drawTextOnDraggableCanvas();
                }
            });
        }
    });

    paintButton.addEventListener('click', (e) => {
        setAppMode(APP_MODES.DRAWING);
    });

    drawBoxButton.addEventListener('click', (e) => {
        setAppMode(APP_MODES.DRAW_BOX);
    });

    fillBoxButton.addEventListener('click', (e) => {
        setAppMode(APP_MODES.FILL_BOX);
    });

    textButton.addEventListener('click', (e) => {
        setAppMode(APP_MODES.TEXT);
    });

    clearButton.addEventListener('click', (e) => {
        workContext.clearRect(0, 0, workCanvas.width, workCanvas.height);
        mainContext.fillStyle = style(selectedColor);
        mainContext.fillRect(0, 0, mainCanvas.width, mainCanvas.height);
        setAppMode(APP_MODES.DEFAULT);
    });

    uploadButton.addEventListener('click', (e) => {
        uploadCanvas();
    });

    function drawTextOnDraggableCanvas() {
        const margin = 10; // pixels around text
        draggableContext.font = `${fontSize} ${fontName}`;
        const {
            actualBoundingBoxAscent,
            actualBoundingBoxDescent,
            actualBoundingBoxLeft,
            actualBoundingBoxRight
        } = draggableContext.measureText(text);
        const actualWidth = (actualBoundingBoxRight - actualBoundingBoxLeft);
        const actualHeight = (actualBoundingBoxAscent + actualBoundingBoxDescent);
        if (SIDEWAYS) {
            draggableCanvas.width = 2 * margin + actualHeight;
            draggableCanvas.height = 2 * margin + actualWidth;

        } else {
            draggableCanvas.width = 2 * margin + actualWidth;
            draggableCanvas.height = 2 * margin + actualHeight;
        }

        draggableContext.font = `${fontSize} ${fontName}`; // have to do this again after setting size
        draggableContext.fillStyle = style(selectedColor);
        draggableContext.clearRect(0, 0, draggableCanvas.width, draggableCanvas.height);

        if (SIDEWAYS) {
            draggableContext.save();
            draggableContext.rotate(Math.PI / 2);
            draggableContext.translate(0, -(2 * margin) - actualHeight);
            // draggableContext.translate(0, margin + actualHeight);
            draggableContext.fillText(text, margin, margin + actualHeight);
            draggableContext.restore();
        } else {
            draggableContext.fillText(text, margin, margin + actualHeight);
        }
    }

    fontNameSelect.addEventListener('change', (e) => {
       fontName = e.target.value;
       drawTextOnDraggableCanvas();
    });

    fontSizeSelect.addEventListener('change', (e) => {
        fontSize = e.target.value;
        drawTextOnDraggableCanvas();
    })

    document.addEventListener('keydown', function (e) {
        const { key, shiftKey } = e;
        if (key === 'Escape') {
            setAppMode(APP_MODES.DEFAULT);
        }
        if (appMode === APP_MODES.PASTE_OPERATION) {
            if (key === 'Enter') {
                transferDraggableToMain();
            }
        }
        if (appMode === APP_MODES.TEXT) {
            if (text.length > 0) {
                if (key === 'Backspace') {
                    text = text.substring(0, text.length - 1);
                } else if (key === 'Enter') {
                    transferDraggableToMain();
                    return;
                }
            }
            if (key.length === 1) {
                text += key;
            }
            drawTextOnDraggableCanvas();
        }
    });
}

window.onload = function() {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            // Request finished
            if (xhr.status === 200 && xhr.responseText) {
                const lines = xhr.responseText.split('\n');
                let device = '';
                lines.forEach((line) => {
                    const hashpos = line.indexOf('#');
                    const match = (hashpos === -1 ? line : line.substring(0, hashpos)).match(/device\s*=\s*"?(\w+)"?/);
                    if (match) {
                        device = match[1];
                    }
                });
                main(device);
            } else {
                main(xhr.status === 404 ? 'EPD_5in65' : ''); // Pico reports no device.txt file; default to EPD_5in65
            }
        }
    };
    xhr.open("GET", '/device.txt');
    xhr.send();
}

// window.onload = main;