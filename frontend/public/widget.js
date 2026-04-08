(function () {
  const script = document.currentScript;
  const botId = script.getAttribute("data-bot-id");
  const API_BASE = "http://127.0.0.1:8000";

  if (!botId) {
    console.error("Chatbot Widget: Missing data-bot-id attribute.");
    return;
  }

  // Define unique styles
  const styles = `
    .cb-widget-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .cb-bubble {
      width: 60px;
      height: 60px;
      background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(37, 99, 235, 0.4);
      transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
      animation: cb-pulse 4s infinite;
    }
    @keyframes cb-pulse {
      0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7); }
      70% { box-shadow: 0 0 0 15px rgba(37, 99, 235, 0); }
      100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
    }
    .cb-bubble:hover {
      transform: scale(1.1) translateY(-2px);
      box-shadow: 0 8px 24px rgba(37, 99, 235, 0.5);
    }
    .cb-bubble svg {
      width: 28px;
      height: 28px;
      fill: white;
      transition: transform 0.3s ease;
    }
    .cb-bubble:hover svg {
      transform: rotate(10deg);
    }
    .cb-window {
      position: fixed;
      bottom: 100px;
      right: 24px;
      width: 380px;
      height: 560px;
      min-width: 300px;
      min-height: 400px;
      background: white;
      border-radius: 20px;
      box-shadow: 0 16px 48px rgba(0, 0, 0, 0.15);
      display: none;
      flex-direction: column;
      overflow: hidden;
      transform-origin: bottom right;
      transition: opacity 0.3s cubic-bezier(0.19, 1, 0.22, 1), transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
      opacity: 0;
      transform: translateY(20px) scale(0.95);
    }
    .cb-window.cb-open {
      display: flex;
      opacity: 1;
      transform: translateY(0) scale(1);
    }
    .cb-header {
      background: linear-gradient(90deg, #2563eb 0%, #4f46e5 100%);
      color: white;
      padding: 18px 24px;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
      cursor: grab;
      user-select: none;
      flex-shrink: 0;
    }
    .cb-header.cb-dragging {
      cursor: grabbing;
    }
    .cb-avatar {
      width: 36px;
      height: 36px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      flex-shrink: 0;
    }
    .cb-header-info {
      flex: 1;
      min-width: 0;
    }
    .cb-header-title {
      font-weight: 700;
      font-size: 16px;
      letter-spacing: -0.01em;
      margin: 0;
      display: block;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .cb-header-status {
      font-size: 12px;
      opacity: 0.8;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .cb-header-status::before {
      content: "";
      width: 6px;
      height: 6px;
      background: #4ade80;
      border-radius: 50%;
    }
    .cb-messages {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 16px;
      scroll-behavior: smooth;
    }
    /* Simple Modern Scrollbar */
    .cb-messages::-webkit-scrollbar {
      width: 4px;
    }
    .cb-messages::-webkit-scrollbar-track {
      background: transparent;
    }
    .cb-messages::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 10px;
    }
    .cb-message {
      max-width: 85%;
      padding: 12px 16px;
      font-size: 14px;
      line-height: 1.6;
      position: relative;
      animation: cb-msg-in 0.3s ease-out;
    }
    @keyframes cb-msg-in {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .cb-message-bot {
      align-self: flex-start;
      background: white;
      color: #334155;
      border-radius: 16px 16px 16px 4px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      border: 1px solid #f1f5f9;
    }
    .cb-message-user {
      align-self: flex-end;
      background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
      color: white;
      border-radius: 16px 16px 4px 16px;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    .cb-input-area {
      padding: 18px 24px;
      background: white;
      border-top: 1px solid #f1f5f9;
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex-shrink: 0;
    }
    .cb-input-wrapper {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .cb-input {
      flex: 1;
      border: 2px solid #f1f5f9;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 14px;
      outline: none;
      transition: all 0.2s ease;
      background: #f8fafc;
    }
    .cb-input:focus {
      background: white;
      border-color: #2563eb;
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
    }
    .cb-input:disabled {
      background: #f1f5f9;
      opacity: 0.6;
    }
    .cb-send {
      background: #2563eb;
      color: white;
      border: none;
      width: 44px;
      height: 44px;
      border-radius: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
      flex-shrink: 0;
    }
    .cb-send:hover:not(:disabled) {
      background: #1d4ed8;
      transform: translateY(-1px);
    }
    .cb-send:active:not(:disabled) {
      transform: translateY(0);
    }
    .cb-send:disabled {
      background: #cbd5e1;
      box-shadow: none;
      cursor: not-allowed;
    }
    .cb-send svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2.5;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .cb-loader {
      align-self: flex-start;
      padding: 12px 16px;
      background: white;
      border-radius: 16px 16px 16px 4px;
      display: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      border: 1px solid #f1f5f9;
      margin-bottom: 4px;
    }
    .cb-loader span {
      animation: cb-dot-bounce 1.2s infinite;
      display: inline-block;
      width: 6px;
      height: 6px;
      background: #94a3b8;
      border-radius: 50%;
      margin: 0 2px;
    }
    .cb-loader span:nth-child(2) { animation-delay: 0.2s; }
    .cb-loader span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes cb-dot-bounce {
      0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
      30% { transform: translateY(-4px); opacity: 1; }
    }
    .cb-quick-start {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
      padding: 0 8px;
      animation: cb-fade-in-up 0.5s ease-out 0.8s both;
    }
    @keyframes cb-fade-in-up {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .cb-suggestion-btn {
      font-size: 11px;
      font-weight: 700;
      color: #64748b;
      background: white;
      border: 1px solid #e2e8f0;
      border-radius: 9999px;
      padding: 8px 16px;
      cursor: pointer;
      transition: all 0.2s;
      text-align: left;
    }
    .cb-suggestion-btn:hover {
      border-color: #818cf8;
      color: #4f46e5;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .cb-suggestion-btn:active {
      transform: scale(0.95);
    }
    /* 8-direction resize handles */
    .cb-rh {
      position: absolute;
      z-index: 10;
      user-select: none;
    }
    /* Edges */
    .cb-rh-n  { top: 0;    left: 6px;   right: 6px;  height: 6px; cursor: n-resize; }
    .cb-rh-s  { bottom: 0; left: 6px;   right: 6px;  height: 6px; cursor: s-resize; }
    .cb-rh-w  { left: 0;   top: 6px;    bottom: 6px; width: 6px;  cursor: w-resize; }
    .cb-rh-e  { right: 0;  top: 6px;    bottom: 6px; width: 6px;  cursor: e-resize; }
    /* Corners */
    .cb-rh-nw { top: 0;    left: 0;     width: 12px; height: 12px; cursor: nw-resize; border-radius: 20px 0 0 0; }
    .cb-rh-ne { top: 0;    right: 0;    width: 12px; height: 12px; cursor: ne-resize; border-radius: 0 20px 0 0; }
    .cb-rh-sw { bottom: 0; left: 0;     width: 12px; height: 12px; cursor: sw-resize; border-radius: 0 0 0 20px; }
    .cb-rh-se { bottom: 0; right: 0;    width: 12px; height: 12px; cursor: se-resize; border-radius: 0 0 20px 0; }
    .cb-rh:hover { background: rgba(37,99,235,0.12); }
    /* Editable name input */
    .cb-name-input {
      background: rgba(255,255,255,0.15);
      border: 1px solid rgba(255,255,255,0.4);
      border-radius: 6px;
      color: white;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.01em;
      padding: 2px 6px;
      outline: none;
      width: 100%;
      font-family: inherit;
    }
    .cb-name-input::placeholder {
      color: rgba(255,255,255,0.6);
    }
  `;

  const styleTag = document.createElement("style");
  styleTag.innerHTML = styles;
  document.head.appendChild(styleTag);

  // Create UI
  const container = document.createElement("div");
  container.className = "cb-widget-container";
  container.innerHTML = `
    <div class="cb-window" id="cb-window">
      <div class="cb-header" id="cb-header">
        <div class="cb-avatar" id="cb-avatar">AI</div>
        <div class="cb-header-info">
          <span class="cb-header-title" id="cb-bot-name">Chat Support</span>
          <span class="cb-header-status">Online &bull; Ready to assist</span>
        </div>
        <span id="cb-confirm-row" style="display:none;align-items:center;gap:6px;">
          <button id="cb-confirm-yes" style="background:#16a34a;border:none;color:white;cursor:pointer;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;line-height:1.4;">Yes</button>
          <button id="cb-confirm-no"  style="background:rgba(255,255,255,0.2);border:none;color:white;cursor:pointer;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;line-height:1.4;">No</button>
        </span>
        <button id="cb-clear" title="Clear chat" style="background:none;border:none;color:white;cursor:pointer;font-size:16px;opacity:0.75;padding:0 4px;line-height:1;">&#128465;</button>
        <button id="cb-close" style="background:none;border:none;color:white;cursor:pointer;font-size:24px;opacity:0.8;padding:0 4px;">&times;</button>
      </div>
      <div class="cb-messages" id="cb-messages">
        <!-- Messages will be injected here -->
        <div class="cb-loader" id="cb-loader">
          <span></span><span></span><span></span>
        </div>
        <div class="cb-quick-start" id="cb-quick-start" style="display:none;">
          <button class="cb-suggestion-btn" id="cb-chip-1">What can you help me with?</button>
        </div>
      </div>
      <div class="cb-input-area">
        <div class="cb-input-wrapper">
          <input type="text" class="cb-input" id="cb-input" placeholder="Type your message..." autocomplete="off">
          <button class="cb-send" id="cb-send">
            <svg viewBox="0 0 24 24"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"></path></svg>
          </button>
        </div>
      </div>
      <!-- 8-direction resize handles -->
      <div class="cb-rh cb-rh-n"  data-dir="n"></div>
      <div class="cb-rh cb-rh-s"  data-dir="s"></div>
      <div class="cb-rh cb-rh-w"  data-dir="w"></div>
      <div class="cb-rh cb-rh-e"  data-dir="e"></div>
      <div class="cb-rh cb-rh-nw" data-dir="nw"></div>
      <div class="cb-rh cb-rh-ne" data-dir="ne"></div>
      <div class="cb-rh cb-rh-sw" data-dir="sw"></div>
      <div class="cb-rh cb-rh-se" data-dir="se"></div>
    </div>
    <div class="cb-bubble" id="cb-bubble">
      <svg viewBox="0 0 24 24"><path d="M20,2H4C2.9,2,2,2.9,2,4v18l4-4h14c1.1,0,2-0.9,2-2V4C22,2.9,21.1,2,20,2z"/></svg>
    </div>
  `;
  document.body.appendChild(container);

  const bubble = document.getElementById("cb-bubble");
  const windowNode = document.getElementById("cb-window");
  const header = document.getElementById("cb-header");
  const closeBtn = document.getElementById("cb-close");
  const messagesArea = document.getElementById("cb-messages");
  const input = document.getElementById("cb-input");
  const sendBtn = document.getElementById("cb-send");
  const loader = document.getElementById("cb-loader");
  const botNameDisplay = document.getElementById("cb-bot-name");
  const avatarDisplay = document.getElementById("cb-avatar");
  const quickStart = document.getElementById("cb-quick-start");
  const chip1 = document.getElementById("cb-chip-1");
  const clearBtn = document.getElementById("cb-clear");
  const confirmRow = document.getElementById("cb-confirm-row");
  const confirmYes = document.getElementById("cb-confirm-yes");
  const confirmNo = document.getElementById("cb-confirm-no");

  let isOpen = false;
  let botData = null;

  // ─── 1. Suggestion chips: hide permanently after first interaction ──────────
  let chipsHidden = false;

  function hideChipsPermanently() {
    if (chipsHidden) return;
    chipsHidden = true;
    if (quickStart) quickStart.style.display = "none";
  }

  // ─── 2. Draggable widget ────────────────────────────────────────────────────
  // Widget starts as fixed bottom-right; once dragged, we switch to absolute
  // positioning relative to viewport (left/top) so it stays where dropped.

  let isDragging = false;
  let dragOffsetX = 0;
  let dragOffsetY = 0;

  // Track whether widget has been manually positioned
  let isPositioned = false;

  header.addEventListener("mousedown", function (e) {
    // Prevent drag from triggering on the close button
    if (e.target === closeBtn || closeBtn.contains(e.target)) return;
    // Prevent drag from triggering on the editable name input
    if (e.target.classList && e.target.classList.contains("cb-name-input")) return;

    isDragging = true;
    header.classList.add("cb-dragging");

    const rect = windowNode.getBoundingClientRect();

    // On first drag, convert from bottom/right anchoring to top/left
    if (!isPositioned) {
      windowNode.style.bottom = "auto";
      windowNode.style.right = "auto";
      windowNode.style.top = rect.top + "px";
      windowNode.style.left = rect.left + "px";
      isPositioned = true;
    }

    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;

    e.preventDefault();
  });

  // (drag mousemove + mouseup merged into the single handler below with resize)

  // ─── 2b. Full 8-direction resize ─────────────────────────────────────────────
  let activeResizeDir = null; // 'n'|'s'|'e'|'w'|'nw'|'ne'|'sw'|'se'
  let resizeStartX = 0;
  let resizeStartY = 0;
  let resizeStartW = 0;
  let resizeStartH = 0;
  let resizeStartLeft = 0;
  let resizeStartTop = 0;

  function anchorToTopLeft() {
    if (!isPositioned) {
      const rect = windowNode.getBoundingClientRect();
      windowNode.style.bottom = "auto";
      windowNode.style.right = "auto";
      windowNode.style.top = rect.top + "px";
      windowNode.style.left = rect.left + "px";
      isPositioned = true;
    }
  }

  // Attach mousedown to every resize handle via event delegation
  windowNode.addEventListener("mousedown", function (e) {
    const handle = e.target.closest(".cb-rh");
    if (!handle) return;
    anchorToTopLeft();
    const rect = windowNode.getBoundingClientRect();
    activeResizeDir = handle.dataset.dir;
    resizeStartX = e.clientX;
    resizeStartY = e.clientY;
    resizeStartW = windowNode.offsetWidth;
    resizeStartH = windowNode.offsetHeight;
    resizeStartLeft = rect.left;
    resizeStartTop = rect.top;
    e.preventDefault();
    e.stopPropagation();
  });

  // Single merged mousemove handler on document
  document.addEventListener("mousemove", function (e) {
    if (isDragging) {
      const newLeft = e.clientX - dragOffsetX;
      const newTop = e.clientY - dragOffsetY;
      const W = windowNode.offsetWidth;
      const H = windowNode.offsetHeight;
      windowNode.style.left = Math.max(0, Math.min(window.innerWidth - W, newLeft)) + "px";
      windowNode.style.top = Math.max(0, Math.min(window.innerHeight - H, newTop)) + "px";
      e.preventDefault();
    }
    if (activeResizeDir) {
      const dx = e.clientX - resizeStartX;
      const dy = e.clientY - resizeStartY;
      const MIN_W = 300, MIN_H = 400;
      const dir = activeResizeDir;

      // ── Width / left ──
      if (dir === 'e' || dir === 'ne' || dir === 'se') {
        // right edge: grow right
        windowNode.style.width = Math.max(MIN_W, resizeStartW + dx) + "px";
      }
      if (dir === 'w' || dir === 'nw' || dir === 'sw') {
        // left edge: grow left (left moves, width grows)
        const newW = Math.max(MIN_W, resizeStartW - dx);
        windowNode.style.width = newW + "px";
        windowNode.style.left = (resizeStartLeft + resizeStartW - newW) + "px";
      }

      // ── Height / top ──
      if (dir === 's' || dir === 'se' || dir === 'sw') {
        // bottom edge: grow down
        windowNode.style.height = Math.max(MIN_H, resizeStartH + dy) + "px";
      }
      if (dir === 'n' || dir === 'nw' || dir === 'ne') {
        // top edge: grow up (top moves, height grows)
        const newH = Math.max(MIN_H, resizeStartH - dy);
        windowNode.style.height = newH + "px";
        windowNode.style.top = (resizeStartTop + resizeStartH - newH) + "px";
      }

      e.preventDefault();
    }
  });

  document.addEventListener("mouseup", function () {
    isDragging = false;
    activeResizeDir = null;
    header.classList.remove("cb-dragging");
  });

  // ─── 3. Editable bot name (double-click) ────────────────────────────────────
  const NAME_KEY = "widget_custom_bot_name";

  function enterNameEditMode() {
    const currentName = botNameDisplay.innerText || "";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.value = currentName;
    nameInput.className = "cb-name-input";
    nameInput.placeholder = "Bot name...";

    // Replace span with input
    botNameDisplay.style.display = "none";
    botNameDisplay.parentNode.insertBefore(nameInput, botNameDisplay);
    nameInput.focus();
    nameInput.select();

    function saveAndExit() {
      const newName = nameInput.value.trim() || currentName;
      botNameDisplay.innerText = newName;
      localStorage.setItem(NAME_KEY, newName);
      // Update avatar initial
      if (avatarDisplay) avatarDisplay.innerText = newName.substring(0, 1).toUpperCase() || "AI";
      nameInput.remove();
      botNameDisplay.style.display = "";
    }

    nameInput.addEventListener("blur", saveAndExit);
    nameInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        nameInput.blur();
      } else if (e.key === "Escape") {
        nameInput.value = currentName;
        nameInput.blur();
      }
    });
  }

  botNameDisplay.style.cursor = "text";
  botNameDisplay.title = "Click to rename";
  botNameDisplay.addEventListener("click", function (e) {
    e.stopPropagation(); // prevent drag from starting
    enterNameEditMode();
  });

  // ─── Bot data fetch ─────────────────────────────────────────────────────────
  async function fetchBotData() {
    try {
      const res = await fetch(`${API_BASE}/bots/${botId}`);
      if (!res.ok) throw new Error("Bot not found");
      botData = await res.json();

      // Apply stored custom name (overrides API name if user renamed it)
      const storedName = localStorage.getItem(NAME_KEY);
      const displayName = storedName || botData.name || "Chat Support";

      if (botNameDisplay) botNameDisplay.innerText = displayName;
      if (avatarDisplay) avatarDisplay.innerText = displayName ? displayName.substring(0, 1).toUpperCase() : "AI";

      // Initial greeting flow
      loader.style.display = "block";
      messagesArea.scrollTop = messagesArea.scrollHeight;

      await new Promise(resolve => setTimeout(resolve, 800));

      loader.style.display = "none";
      const greeting = botData.greeting || "Hi! How can I help you today?";
      const greetingElement = addMessage("", "bot", true);
      await simulateStreaming(greetingElement, greeting);

      // Show suggestion chips (only if conversation hasn't started)
      if (!chipsHidden && quickStart) {
        quickStart.style.display = "flex";
      }

    } catch (err) {
      console.error("Chatbot Widget Error:", err);
      addMessage("Something went wrong. Please try again.", "bot");
    }
  }

  function addMessage(text, sender, isTyping = false) {
    const msg = document.createElement("div");
    msg.className = `cb-message cb-message-${sender}`;
    if (!isTyping) msg.innerText = text;
    messagesArea.insertBefore(msg, loader);
    messagesArea.scrollTop = messagesArea.scrollHeight;
    return msg;
  }

  async function simulateStreaming(element, text) {
    let currentText = "";
    const speed = 25;

    for (let i = 0; i < text.length; i++) {
      currentText += text[i];
      element.innerText = currentText;
      messagesArea.scrollTop = messagesArea.scrollHeight;
      await new Promise(resolve => setTimeout(resolve, speed));
    }
  }

  async function handleSend() {
    const question = input.value.trim();
    if (!question || loader.style.display === "block") return;

    // Hide chips permanently on first real message
    hideChipsPermanently();

    addMessage(question, "user");
    input.value = "";
    input.disabled = true;
    sendBtn.disabled = true;

    loader.style.display = "block";
    messagesArea.scrollTop = messagesArea.scrollHeight;

    try {
      const res = await fetch(`${API_BASE}/chat/${botId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });
      if (!res.ok) throw new Error("Chat failed");
      const data = await res.json();

      loader.style.display = "none";

      const botMsgElement = addMessage("", "bot", true);
      await simulateStreaming(botMsgElement, data.answer);

    } catch (err) {
      console.error("Chat Error:", err);
      loader.style.display = "none";
      addMessage("Something went wrong. Please try again.", "bot");
    } finally {
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // ─── Chip click handler ──────────────────────────────────────────────────────
  chip1.addEventListener("click", function () {
    hideChipsPermanently();
    input.value = chip1.innerText;
    handleSend();
  });

  // ─── Clear chat — inline Yes/No confirmation ─────────────────────────────────
  function doClearChat() {
    const msgs = messagesArea.querySelectorAll(".cb-message");
    msgs.forEach(function (m) { m.remove(); });
    if (chipsHidden && quickStart) quickStart.style.display = "none";
    if (botData) {
      const greetingText = botData.greeting || "Hi! How can I help you today?";
      const greetingEl = addMessage("", "bot", true);
      simulateStreaming(greetingEl, greetingText);
    }
  }

  function showConfirmRow() {
    clearBtn.style.display = "none";
    confirmRow.style.display = "inline-flex";
  }

  function hideConfirmRow() {
    confirmRow.style.display = "none";
    clearBtn.style.display = "";
  }

  clearBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    showConfirmRow();
  });

  confirmYes.addEventListener("click", function (e) {
    e.stopPropagation();
    hideConfirmRow();
    doClearChat();
  });

  confirmNo.addEventListener("click", function (e) {
    e.stopPropagation();
    hideConfirmRow();
  });

  // ─── Toggle open/close ───────────────────────────────────────────────────────
  bubble.onclick = () => {
    isOpen = !isOpen;
    if (isOpen) {
      windowNode.style.display = "flex";
      setTimeout(() => {
        windowNode.classList.add("cb-open");
        if (!botData) fetchBotData();
        input.focus();
      }, 10);
    } else {
      windowNode.classList.remove("cb-open");
      setTimeout(() => {
        windowNode.style.display = "none";
      }, 300);
    }
  };

  closeBtn.onclick = () => {
    isOpen = false;
    windowNode.classList.remove("cb-open");
    setTimeout(() => {
      windowNode.style.display = "none";
    }, 300);
  };

  sendBtn.onclick = handleSend;
  input.onkeypress = (e) => {
    if (e.key === "Enter") handleSend();
  };

})();
