window.addEventListener('DOMContentLoaded', function() {
    const term = new Terminal({
        cursorBlink: false,
        macOptionIsMeta: true,
        allowTransparency: true,
        altClickMovesCursor: false,
        fontFamily: 'Cascadia Code, Courier New, Courier, -apple-system, Noto Sans, Helvetica Neue, Helvetica, Nimbus Sans L, Arial, Liberation Sans, PingFang SC, Hiragino Sans GB, Noto Sans CJK SC, Source Han Sans SC, Source Han Sans CN, Microsoft YaHei, Wenquanyi Micro Hei, WenQuanYi Zen Hei, ST Heiti, SimHei, WenQuanYi Zen Hei Sharp, sans-serif',
        cursorStyle: 'bar',
        minimumContrastRatio: 7,
        smoothScrollDuration: 150,
        scrollback: 100000,
        rightClickSelectsWord: false,
        theme: {
            background: '#ffffff00',
            foreground: '#303030',
            cursor: '#303030',
            cursorAccent: '#ffffff00',
            selectionBackground: '#b1e2facc',
            selectionForeground: '#303030',
            selectionInactiveBackground: '#d8d8d8cc',
        }
    });

    const fit = new FitAddon.FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new SearchAddon.SearchAddon());

    term.open(document.getElementById("terminal"));
    fit.fit();
    console.debug("Web console init: ", term.cols, term.rows);

    const basePrefix = document.documentElement.getAttribute('data-prefix') || '';
    const socket = io.connect("/pty", {'reconnection': false, 'transports': ['websocket']});
    const statusMsg = document.getElementById("status-msg");
    const statusIcon = document.getElementById("status-icon");
    const xiguaUrl = document.getElementById("xigua-url");
    const runOnceBtn = document.getElementById("run-once-btn");
    const scheduleStartBtn = document.getElementById("schedule-start-btn");
    const scheduleStopBtn = document.getElementById("schedule-stop-btn");

    function resize() {
        fit.fit();
        console.debug("Web console resize: ", term.cols, term.rows);
        const dims = { cols: term.cols, rows: term.rows };
        socket.emit("resize", dims);
    }

    function debounce(func, wait_ms) {
        let timeout;
        return function (...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait_ms);
        };
    }

    function customKeyEventHandler(e) {
        if (e.type !== "keydown") {
            return true;
        }
        if (e.ctrlKey) {
            const key = e.key.toLowerCase();
            if (key === "v") {
                navigator.clipboard.readText().then((toPaste) => {
                    term.writeText(toPaste);
                });
                return false;
            } else if (key === "c" || key === "x") {
                const toCopy = term.getSelection();
                navigator.clipboard.writeText(toCopy);
                term.focus();
                return false;
            }
        }
        return true;
    }

    window.onresize = debounce(resize, 50);
    term.attachCustomKeyEventHandler(customKeyEventHandler);
    term.onData((data) => {
        console.debug(data)
        socket.emit("pty-input", { input: data });
    });

    function setStatus(payload) {
        if (payload.mode === 'scheduled') {
            statusIcon.style.backgroundColor = 'green';
            statusMsg.textContent = '定时运行中';
        } else if (payload.mode === 'running') {
            statusIcon.style.backgroundColor = 'green';
            statusMsg.textContent = '任务运行中';
        } else {
            statusIcon.style.backgroundColor = '#9ca3af';
            statusMsg.textContent = '空闲';
        }
    }

    function refreshStatus() {
        axios.get(basePrefix + '/api/runtime/status')
            .then(function(response) {
                setStatus(response.data);
            })
            .catch(function(error) {
                console.error(error);
                statusIcon.style.backgroundColor = 'red';
                statusMsg.textContent = '状态获取失败';
            });
    }

    function refreshXiguaUrl() {
        axios.get(basePrefix + '/api/xigua/latest')
            .then(function(response) {
                if (response.data.ok && response.data.url) {
                    xiguaUrl.textContent = response.data.url;
                } else {
                    xiguaUrl.textContent = response.data.error || '还没有生成过西瓜签到链接';
                }
            })
            .catch(function(error) {
                console.error(error);
                xiguaUrl.textContent = '读取西瓜链接失败';
            });
    }

    function triggerRuntime(endpoint) {
        axios.post(basePrefix + endpoint)
            .then(function(response) {
                setStatus(response.data.status);
                refreshXiguaUrl();
            })
            .catch(function(error) {
                console.error(error);
                statusMsg.textContent = error.response?.data?.error || '操作失败';
                statusIcon.style.backgroundColor = 'red';
            });
    }

    runOnceBtn.addEventListener('click', function() {
        triggerRuntime('/api/runtime/run-once');
    });

    scheduleStartBtn.addEventListener('click', function() {
        triggerRuntime('/api/runtime/schedule/start');
    });

    scheduleStopBtn.addEventListener('click', function() {
        triggerRuntime('/api/runtime/schedule/stop');
    });

    document.getElementById("xigua-copy-btn").addEventListener('click', function() {
        navigator.clipboard.writeText(xiguaUrl.textContent || '');
    });

    socket.on("connect_error", (error) => {
        console.error("Connection error:", error);
    });

    socket.on("error", (error) => {
        console.error("Socket error:", error);
    });

    socket.on("disconnect", (reason) => {
        statusIcon.style.backgroundColor = "red";
        statusMsg.textContent = "已断开连接";
        console.info("Web console disconnected: ", reason);
    });

    socket.on("pty-output", (data) => {
        console.log("Received pty-output, length:", data.output.length);
        term.write(data.output);
    });

    socket.on("connect", () => {
        console.log("Socket connected");
        console.info("Web console connected: ", term.cols, term.rows);
        term.focus();

        const dims = { cols: term.cols, rows: term.rows };
        console.log("Sending embykeeper_start with dims:", dims);
        socket.emit("embykeeper_start", dims, (error) => {
            if (error) {
                console.error("Failed to start embykeeper:", error);
            }
        });
        refreshStatus();
        refreshXiguaUrl();
    });

    socket.on("runtime-status", (payload) => {
        setStatus(payload);
    });

    refreshStatus();
    refreshXiguaUrl();
    setInterval(refreshStatus, 5000);
    setInterval(refreshXiguaUrl, 10000);

    window.addEventListener('beforeunload', () => {
        if (socket.connected) {
            socket.disconnect();
        }
    });
});
